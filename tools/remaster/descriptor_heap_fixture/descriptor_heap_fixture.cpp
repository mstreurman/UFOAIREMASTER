#include <vulkan/vulkan.h>

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#ifndef VK_EXT_descriptor_heap
#error "Vulkan headers do not expose VK_EXT_descriptor_heap"
#endif

namespace {

constexpr uint32_t kIntelVendorId = 0x8086;
constexpr uint32_t kArcB580DeviceId = 0xe20b;
constexpr uint32_t kDefaultIterations = 256;
constexpr VkDeviceSize kResourceUserBytes = 4096;
constexpr VkDeviceSize kSamplerUserBytes = 1024;

struct GpuShaderRoot {
    uint64_t sceneRootAddress;
    uint64_t frameConstantsAddress;
    uint64_t viewConstantsAddress;
    uint64_t passDataAddress;
};
static_assert(sizeof(GpuShaderRoot) == 32);

struct Args {
    std::string shaderPath;
    uint32_t iterations = kDefaultIterations;
};

[[noreturn]] void fail(const std::string& message) {
    throw std::runtime_error(message);
}

void vkCheck(VkResult result, std::string_view what) {
    if (result != VK_SUCCESS) {
        std::ostringstream out;
        out << what << " failed with VkResult " << static_cast<int>(result);
        fail(out.str());
    }
}

template <typename T>
T vkStruct(VkStructureType sType) {
    T value{};
    value.sType = sType;
    return value;
}

VkDeviceAddress alignUp(VkDeviceAddress value, VkDeviceSize alignment) {
    if (alignment == 0 || (alignment & (alignment - 1)) != 0)
        fail("descriptor heap alignment is not a non-zero power of two");
    const VkDeviceAddress mask = alignment - 1;
    return (value + mask) & ~mask;
}

std::string hexBytes(const uint8_t* data, size_t size) {
    std::ostringstream out;
    out << std::hex << std::setfill('0');
    for (size_t i = 0; i < size; ++i)
        out << std::setw(2) << static_cast<unsigned>(data[i]);
    return out.str();
}

std::string apiVersionString(uint32_t v) {
    std::ostringstream out;
    out << VK_API_VERSION_MAJOR(v) << '.' << VK_API_VERSION_MINOR(v) << '.' << VK_API_VERSION_PATCH(v);
    return out.str();
}

std::vector<uint32_t> readSpirv(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file)
        fail("cannot open SPIR-V file: " + path);
    const std::streamsize bytes = file.tellg();
    if (bytes <= 0 || (bytes % 4) != 0)
        fail("invalid SPIR-V byte size");
    file.seekg(0, std::ios::beg);
    std::vector<uint32_t> words(static_cast<size_t>(bytes) / 4);
    if (!file.read(reinterpret_cast<char*>(words.data()), bytes))
        fail("cannot read SPIR-V file");
    return words;
}

Args parseArgs(int argc, char** argv) {
    Args args;
    for (int i = 1; i < argc; ++i) {
        const std::string_view token(argv[i]);
        if (token == "--shader") {
            if (++i >= argc)
                fail("--shader requires a path");
            args.shaderPath = argv[i];
        } else if (token == "--iterations") {
            if (++i >= argc)
                fail("--iterations requires an integer");
            const unsigned long value = std::stoul(argv[i]);
            if (value == 0 || value > 100000)
                fail("--iterations must be between 1 and 100000");
            args.iterations = static_cast<uint32_t>(value);
        } else if (token == "--help") {
            std::cout << "usage: m0_descriptor_heap_fixture --shader FILE [--iterations N]\n";
            std::exit(0);
        } else {
            fail("unknown argument: " + std::string(token));
        }
    }
    if (args.shaderPath.empty())
        fail("--shader is required");
    return args;
}

struct ValidationState {
    uint32_t warnings = 0;
    uint32_t errors = 0;
};

VKAPI_ATTR VkBool32 VKAPI_CALL validationCallback(
    VkDebugUtilsMessageSeverityFlagBitsEXT severity,
    VkDebugUtilsMessageTypeFlagsEXT,
    const VkDebugUtilsMessengerCallbackDataEXT* callbackData,
    void* userData) {
    auto* state = static_cast<ValidationState*>(userData);
    if (severity & VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT)
        ++state->errors;
    else if (severity & VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT)
        ++state->warnings;
    std::cerr << "[validation] " << (callbackData && callbackData->pMessage ? callbackData->pMessage : "(no message)") << '\n';
    return VK_FALSE;
}

bool hasExtension(const std::vector<VkExtensionProperties>& extensions, const char* name, uint32_t* specVersion = nullptr) {
    for (const auto& ext : extensions) {
        if (std::strcmp(ext.extensionName, name) == 0) {
            if (specVersion)
                *specVersion = ext.specVersion;
            return true;
        }
    }
    return false;
}

bool hasLayer(const std::vector<VkLayerProperties>& layers, const char* name, VkLayerProperties* found = nullptr) {
    for (const auto& layer : layers) {
        if (std::strcmp(layer.layerName, name) == 0) {
            if (found)
                *found = layer;
            return true;
        }
    }
    return false;
}

uint32_t chooseMemoryType(
    const VkPhysicalDeviceMemoryProperties& props,
    uint32_t typeBits,
    VkMemoryPropertyFlags required,
    VkMemoryPropertyFlags preferred,
    VkMemoryPropertyFlags* selectedFlags = nullptr) {
    std::optional<uint32_t> fallback;
    for (uint32_t i = 0; i < props.memoryTypeCount; ++i) {
        if ((typeBits & (1u << i)) == 0)
            continue;
        const auto flags = props.memoryTypes[i].propertyFlags;
        if ((flags & required) != required)
            continue;
        if ((flags & preferred) == preferred) {
            if (selectedFlags)
                *selectedFlags = flags;
            return i;
        }
        if (!fallback)
            fallback = i;
    }
    if (fallback) {
        if (selectedFlags)
            *selectedFlags = props.memoryTypes[*fallback].propertyFlags;
        return *fallback;
    }
    fail("no compatible Vulkan memory type found");
}

struct Buffer {
    VkBuffer buffer = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    VkDeviceSize size = 0;
    void* mapped = nullptr;
    VkDeviceAddress address = 0;
    VkMemoryPropertyFlags memoryFlags = 0;
};

Buffer createBuffer(
    VkDevice device,
    const VkPhysicalDeviceMemoryProperties& memoryProps,
    VkDeviceSize size,
    VkBufferUsageFlags usage,
    VkMemoryPropertyFlags requiredMemory,
    VkMemoryPropertyFlags preferredMemory,
    bool deviceAddress) {
    Buffer out;
    out.size = size;

    VkBufferCreateInfo createInfo = vkStruct<VkBufferCreateInfo>(VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO);
    createInfo.size = size;
    createInfo.usage = usage;
    createInfo.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    vkCheck(vkCreateBuffer(device, &createInfo, nullptr, &out.buffer), "vkCreateBuffer");

    VkMemoryRequirements req{};
    vkGetBufferMemoryRequirements(device, out.buffer, &req);

    VkMemoryAllocateFlagsInfo flagsInfo = vkStruct<VkMemoryAllocateFlagsInfo>(VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_FLAGS_INFO);
    if (deviceAddress)
        flagsInfo.flags = VK_MEMORY_ALLOCATE_DEVICE_ADDRESS_BIT;

    VkMemoryAllocateInfo allocInfo = vkStruct<VkMemoryAllocateInfo>(VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO);
    allocInfo.pNext = deviceAddress ? &flagsInfo : nullptr;
    allocInfo.allocationSize = req.size;
    allocInfo.memoryTypeIndex = chooseMemoryType(
        memoryProps, req.memoryTypeBits, requiredMemory, preferredMemory, &out.memoryFlags);
    vkCheck(vkAllocateMemory(device, &allocInfo, nullptr, &out.memory), "vkAllocateMemory(buffer)");
    vkCheck(vkBindBufferMemory(device, out.buffer, out.memory, 0), "vkBindBufferMemory");

    if (out.memoryFlags & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT)
        vkCheck(vkMapMemory(device, out.memory, 0, VK_WHOLE_SIZE, 0, &out.mapped), "vkMapMemory(buffer)");

    if (deviceAddress) {
        VkBufferDeviceAddressInfo addressInfo = vkStruct<VkBufferDeviceAddressInfo>(VK_STRUCTURE_TYPE_BUFFER_DEVICE_ADDRESS_INFO);
        addressInfo.buffer = out.buffer;
        out.address = vkGetBufferDeviceAddress(device, &addressInfo);
        if (out.address == 0)
            fail("vkGetBufferDeviceAddress returned zero");
    }
    return out;
}

void destroyBuffer(VkDevice device, Buffer& buffer) {
    if (buffer.mapped)
        vkUnmapMemory(device, buffer.memory);
    if (buffer.buffer)
        vkDestroyBuffer(device, buffer.buffer, nullptr);
    if (buffer.memory)
        vkFreeMemory(device, buffer.memory, nullptr);
    buffer = {};
}

struct Image {
    VkImage image = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    VkFormat format = VK_FORMAT_UNDEFINED;
};

Image createImage(
    VkDevice device,
    const VkPhysicalDeviceMemoryProperties& memoryProps,
    VkFormat format,
    VkImageUsageFlags usage) {
    Image out;
    out.format = format;

    VkImageCreateInfo createInfo = vkStruct<VkImageCreateInfo>(VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO);
    createInfo.imageType = VK_IMAGE_TYPE_2D;
    createInfo.format = format;
    createInfo.extent = {1, 1, 1};
    createInfo.mipLevels = 1;
    createInfo.arrayLayers = 1;
    createInfo.samples = VK_SAMPLE_COUNT_1_BIT;
    createInfo.tiling = VK_IMAGE_TILING_OPTIMAL;
    createInfo.usage = usage;
    createInfo.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    createInfo.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    vkCheck(vkCreateImage(device, &createInfo, nullptr, &out.image), "vkCreateImage");

    VkMemoryRequirements req{};
    vkGetImageMemoryRequirements(device, out.image, &req);
    VkMemoryAllocateInfo allocInfo = vkStruct<VkMemoryAllocateInfo>(VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO);
    allocInfo.allocationSize = req.size;
    allocInfo.memoryTypeIndex = chooseMemoryType(
        memoryProps, req.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT, 0);
    vkCheck(vkAllocateMemory(device, &allocInfo, nullptr, &out.memory), "vkAllocateMemory(image)");
    vkCheck(vkBindImageMemory(device, out.image, out.memory, 0), "vkBindImageMemory");
    return out;
}

void destroyImage(VkDevice device, Image& image) {
    if (image.image)
        vkDestroyImage(device, image.image, nullptr);
    if (image.memory)
        vkFreeMemory(device, image.memory, nullptr);
    image = {};
}

VkImageViewCreateInfo imageViewInfo(VkImage image, VkFormat format) {
    VkImageViewCreateInfo info = vkStruct<VkImageViewCreateInfo>(VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO);
    info.image = image;
    info.viewType = VK_IMAGE_VIEW_TYPE_2D;
    info.format = format;
    info.components = {
        VK_COMPONENT_SWIZZLE_IDENTITY,
        VK_COMPONENT_SWIZZLE_IDENTITY,
        VK_COMPONENT_SWIZZLE_IDENTITY,
        VK_COMPONENT_SWIZZLE_IDENTITY,
    };
    info.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    info.subresourceRange.baseMipLevel = 0;
    info.subresourceRange.levelCount = 1;
    info.subresourceRange.baseArrayLayer = 0;
    info.subresourceRange.layerCount = 1;
    return info;
}

void submitAndWait(VkDevice device, VkQueue queue, VkCommandBuffer cmd) {
    VkFenceCreateInfo fenceInfo = vkStruct<VkFenceCreateInfo>(VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
    VkFence fence = VK_NULL_HANDLE;
    vkCheck(vkCreateFence(device, &fenceInfo, nullptr, &fence), "vkCreateFence");
    VkSubmitInfo submit = vkStruct<VkSubmitInfo>(VK_STRUCTURE_TYPE_SUBMIT_INFO);
    submit.commandBufferCount = 1;
    submit.pCommandBuffers = &cmd;
    vkCheck(vkQueueSubmit(queue, 1, &submit, fence), "vkQueueSubmit");
    vkCheck(vkWaitForFences(device, 1, &fence, VK_TRUE, std::numeric_limits<uint64_t>::max()), "vkWaitForFences");
    vkDestroyFence(device, fence, nullptr);
}

void beginCommand(VkCommandBuffer cmd) {
    VkCommandBufferBeginInfo begin = vkStruct<VkCommandBufferBeginInfo>(VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    vkCheck(vkBeginCommandBuffer(cmd, &begin), "vkBeginCommandBuffer");
}

void imageBarrier(
    VkCommandBuffer cmd,
    VkImage image,
    VkPipelineStageFlags2 srcStage,
    VkAccessFlags2 srcAccess,
    VkPipelineStageFlags2 dstStage,
    VkAccessFlags2 dstAccess,
    VkImageLayout oldLayout,
    VkImageLayout newLayout) {
    VkImageMemoryBarrier2 barrier = vkStruct<VkImageMemoryBarrier2>(VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER_2);
    barrier.srcStageMask = srcStage;
    barrier.srcAccessMask = srcAccess;
    barrier.dstStageMask = dstStage;
    barrier.dstAccessMask = dstAccess;
    barrier.oldLayout = oldLayout;
    barrier.newLayout = newLayout;
    barrier.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    barrier.image = image;
    barrier.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    barrier.subresourceRange.levelCount = 1;
    barrier.subresourceRange.layerCount = 1;

    VkDependencyInfo dep = vkStruct<VkDependencyInfo>(VK_STRUCTURE_TYPE_DEPENDENCY_INFO);
    dep.imageMemoryBarrierCount = 1;
    dep.pImageMemoryBarriers = &barrier;
    vkCmdPipelineBarrier2(cmd, &dep);
}

uint64_t fnv1a(uint64_t state, uint64_t value) {
    constexpr uint64_t prime = 1099511628211ull;
    for (unsigned shift = 0; shift < 64; shift += 8) {
        state ^= static_cast<uint8_t>((value >> shift) & 0xffu);
        state *= prime;
    }
    return state;
}

std::string hex64(uint64_t value) {
    std::ostringstream out;
    out << std::hex << std::setfill('0') << std::setw(16) << value;
    return out.str();
}

} // namespace

int main(int argc, char** argv) {
    VkInstance instance = VK_NULL_HANDLE;
    VkDebugUtilsMessengerEXT messenger = VK_NULL_HANDLE;
    VkDevice device = VK_NULL_HANDLE;
    VkShaderModule shaderModule = VK_NULL_HANDLE;
    VkPipeline pipeline = VK_NULL_HANDLE;
    VkCommandPool commandPool = VK_NULL_HANDLE;
    VkCommandBuffer commandBuffer = VK_NULL_HANDLE;
    Buffer samplerHeap{};
    Buffer resourceHeap{};
    Buffer staging{};
    Buffer words{};
    Buffer readback{};
    Image sourceA{};
    Image sourceB{};
    Image output{};

    try {
        const Args args = parseArgs(argc, argv);
        const auto spirv = readSpirv(args.shaderPath);

        uint32_t loaderVersion = VK_API_VERSION_1_0;
        if (auto enumerateVersion = reinterpret_cast<PFN_vkEnumerateInstanceVersion>(
                vkGetInstanceProcAddr(VK_NULL_HANDLE, "vkEnumerateInstanceVersion"))) {
            vkCheck(enumerateVersion(&loaderVersion), "vkEnumerateInstanceVersion");
        }
        if (loaderVersion < VK_API_VERSION_1_4)
            fail("Vulkan loader does not expose Vulkan 1.4");

        uint32_t layerCount = 0;
        vkCheck(vkEnumerateInstanceLayerProperties(&layerCount, nullptr), "vkEnumerateInstanceLayerProperties(count)");
        std::vector<VkLayerProperties> layers(layerCount);
        vkCheck(vkEnumerateInstanceLayerProperties(&layerCount, layers.data()), "vkEnumerateInstanceLayerProperties(list)");
        VkLayerProperties validationLayer{};
        if (!hasLayer(layers, "VK_LAYER_KHRONOS_validation", &validationLayer))
            fail("VK_LAYER_KHRONOS_validation is not installed");

        uint32_t instanceExtCount = 0;
        vkCheck(vkEnumerateInstanceExtensionProperties(nullptr, &instanceExtCount, nullptr), "vkEnumerateInstanceExtensionProperties(count)");
        std::vector<VkExtensionProperties> instanceExts(instanceExtCount);
        vkCheck(vkEnumerateInstanceExtensionProperties(nullptr, &instanceExtCount, instanceExts.data()), "vkEnumerateInstanceExtensionProperties(list)");
        if (!hasExtension(instanceExts, VK_EXT_DEBUG_UTILS_EXTENSION_NAME))
            fail("VK_EXT_debug_utils is required for validation capture");

        ValidationState validation{};
        VkDebugUtilsMessengerCreateInfoEXT debugInfo = vkStruct<VkDebugUtilsMessengerCreateInfoEXT>(VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT);
        debugInfo.messageSeverity = VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT |
                                    VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT;
        debugInfo.messageType = VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT |
                                VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT |
                                VK_DEBUG_UTILS_MESSAGE_TYPE_PERFORMANCE_BIT_EXT;
        debugInfo.pfnUserCallback = validationCallback;
        debugInfo.pUserData = &validation;

        VkApplicationInfo app = vkStruct<VkApplicationInfo>(VK_STRUCTURE_TYPE_APPLICATION_INFO);
        app.pApplicationName = "UFOAI M0.7 descriptor heap fixture";
        app.applicationVersion = 1;
        app.pEngineName = "none";
        app.engineVersion = 1;
        app.apiVersion = VK_API_VERSION_1_4;

        const char* enabledLayer = "VK_LAYER_KHRONOS_validation";
        const char* enabledInstanceExt = VK_EXT_DEBUG_UTILS_EXTENSION_NAME;
        VkInstanceCreateInfo instanceInfo = vkStruct<VkInstanceCreateInfo>(VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO);
        instanceInfo.pNext = &debugInfo;
        instanceInfo.pApplicationInfo = &app;
        instanceInfo.enabledLayerCount = 1;
        instanceInfo.ppEnabledLayerNames = &enabledLayer;
        instanceInfo.enabledExtensionCount = 1;
        instanceInfo.ppEnabledExtensionNames = &enabledInstanceExt;
        vkCheck(vkCreateInstance(&instanceInfo, nullptr, &instance), "vkCreateInstance");

        auto createDebug = reinterpret_cast<PFN_vkCreateDebugUtilsMessengerEXT>(
            vkGetInstanceProcAddr(instance, "vkCreateDebugUtilsMessengerEXT"));
        auto destroyDebug = reinterpret_cast<PFN_vkDestroyDebugUtilsMessengerEXT>(
            vkGetInstanceProcAddr(instance, "vkDestroyDebugUtilsMessengerEXT"));
        if (!createDebug || !destroyDebug)
            fail("VK_EXT_debug_utils entry points are unavailable");
        vkCheck(createDebug(instance, &debugInfo, nullptr, &messenger), "vkCreateDebugUtilsMessengerEXT");

        uint32_t physicalCount = 0;
        vkCheck(vkEnumeratePhysicalDevices(instance, &physicalCount, nullptr), "vkEnumeratePhysicalDevices(count)");
        if (physicalCount == 0)
            fail("no Vulkan physical devices found");
        std::vector<VkPhysicalDevice> physicals(physicalCount);
        vkCheck(vkEnumeratePhysicalDevices(instance, &physicalCount, physicals.data()), "vkEnumeratePhysicalDevices(list)");

        VkPhysicalDevice physical = VK_NULL_HANDLE;
        VkPhysicalDeviceProperties baseProps{};
        for (VkPhysicalDevice candidate : physicals) {
            VkPhysicalDeviceProperties props{};
            vkGetPhysicalDeviceProperties(candidate, &props);
            if (props.vendorID == kIntelVendorId && props.deviceID == kArcB580DeviceId) {
                if (physical != VK_NULL_HANDLE)
                    fail("more than one Intel Arc B580 device matches the qualification IDs");
                physical = candidate;
                baseProps = props;
            }
        }
        if (physical == VK_NULL_HANDLE)
            fail("Intel Arc B580 (vendor 0x8086, device 0xe20b) not found; llvmpipe is never an acceptable substitute");
        if (baseProps.deviceType != VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU)
            fail("selected B580 is not reported as a discrete GPU");
        if (baseProps.apiVersion < VK_API_VERSION_1_4)
            fail("selected B580 does not expose Vulkan 1.4");

        VkPhysicalDeviceIDProperties idProps = vkStruct<VkPhysicalDeviceIDProperties>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ID_PROPERTIES);
        VkPhysicalDeviceDriverProperties driverProps = vkStruct<VkPhysicalDeviceDriverProperties>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRIVER_PROPERTIES);
        idProps.pNext = &driverProps;
        VkPhysicalDeviceDescriptorHeapPropertiesEXT heapProps = vkStruct<VkPhysicalDeviceDescriptorHeapPropertiesEXT>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DESCRIPTOR_HEAP_PROPERTIES_EXT);
        driverProps.pNext = &heapProps;
        VkPhysicalDeviceProperties2 props2 = vkStruct<VkPhysicalDeviceProperties2>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2);
        props2.pNext = &idProps;
        vkGetPhysicalDeviceProperties2(physical, &props2);

        uint32_t deviceExtCount = 0;
        vkCheck(vkEnumerateDeviceExtensionProperties(physical, nullptr, &deviceExtCount, nullptr), "vkEnumerateDeviceExtensionProperties(count)");
        std::vector<VkExtensionProperties> deviceExts(deviceExtCount);
        vkCheck(vkEnumerateDeviceExtensionProperties(physical, nullptr, &deviceExtCount, deviceExts.data()), "vkEnumerateDeviceExtensionProperties(list)");
        uint32_t descriptorHeapRevision = 0;
        if (!hasExtension(deviceExts, VK_EXT_DESCRIPTOR_HEAP_EXTENSION_NAME, &descriptorHeapRevision) || descriptorHeapRevision < 1)
            fail("VK_EXT_descriptor_heap revision 1 is required on the selected B580");
        if (!hasExtension(deviceExts, VK_KHR_SHADER_UNTYPED_POINTERS_EXTENSION_NAME))
            fail("VK_KHR_shader_untyped_pointers support is required by the accepted descriptor-heap contract");

        VkPhysicalDeviceDescriptorHeapFeaturesEXT heapFeatures = vkStruct<VkPhysicalDeviceDescriptorHeapFeaturesEXT>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DESCRIPTOR_HEAP_FEATURES_EXT);
        VkPhysicalDeviceShaderUntypedPointersFeaturesKHR untypedFeatures = vkStruct<VkPhysicalDeviceShaderUntypedPointersFeaturesKHR>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_SHADER_UNTYPED_POINTERS_FEATURES_KHR);
        VkPhysicalDeviceVulkan13Features v13Features = vkStruct<VkPhysicalDeviceVulkan13Features>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_3_FEATURES);
        VkPhysicalDeviceVulkan12Features v12Features = vkStruct<VkPhysicalDeviceVulkan12Features>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES);
        heapFeatures.pNext = &untypedFeatures;
        untypedFeatures.pNext = &v13Features;
        v13Features.pNext = &v12Features;
        VkPhysicalDeviceFeatures2 features2 = vkStruct<VkPhysicalDeviceFeatures2>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2);
        features2.pNext = &heapFeatures;
        vkGetPhysicalDeviceFeatures2(physical, &features2);

        if (!heapFeatures.descriptorHeap)
            fail("descriptorHeap feature is false");
        if (!heapFeatures.descriptorHeapCaptureReplay)
            fail("descriptorHeapCaptureReplay feature is false on the B580 qualification target");
        if (!untypedFeatures.shaderUntypedPointers)
            fail("shaderUntypedPointers feature is false on the B580 qualification target");
        if (!v12Features.bufferDeviceAddress)
            fail("bufferDeviceAddress feature is false");
        if (!v13Features.synchronization2)
            fail("synchronization2 feature is false");
        if (!features2.features.shaderInt64)
            fail("shaderInt64 is required by the 32-byte GpuShaderRoot fixture");

        const auto requireEq = [](VkDeviceSize actual, VkDeviceSize expected, const char* name) {
            if (actual != expected) {
                std::ostringstream out;
                out << name << " expected " << expected << " but queried " << actual;
                fail(out.str());
            }
        };
        requireEq(heapProps.samplerHeapAlignment, 64, "samplerHeapAlignment");
        requireEq(heapProps.resourceHeapAlignment, 64, "resourceHeapAlignment");
        requireEq(heapProps.maxSamplerHeapSize, 2147483648ull, "maxSamplerHeapSize");
        requireEq(heapProps.maxResourceHeapSize, 2147483648ull, "maxResourceHeapSize");
        requireEq(heapProps.samplerDescriptorSize, 32, "samplerDescriptorSize");
        requireEq(heapProps.imageDescriptorSize, 64, "imageDescriptorSize");
        requireEq(heapProps.bufferDescriptorSize, 64, "bufferDescriptorSize");
        requireEq(heapProps.samplerDescriptorAlignment, 32, "samplerDescriptorAlignment");
        requireEq(heapProps.imageDescriptorAlignment, 64, "imageDescriptorAlignment");
        requireEq(heapProps.bufferDescriptorAlignment, 64, "bufferDescriptorAlignment");
        requireEq(heapProps.minSamplerHeapReservedRange, 0, "minSamplerHeapReservedRange");
        requireEq(heapProps.minResourceHeapReservedRange, 0, "minResourceHeapReservedRange");
        if (heapProps.maxPushDataSize < sizeof(GpuShaderRoot))
            fail("maxPushDataSize is smaller than GpuShaderRoot");
        if (!heapProps.sparseDescriptorHeaps)
            fail("sparseDescriptorHeaps expected true on reference B580");
        if (heapProps.protectedDescriptorHeaps)
            fail("protectedDescriptorHeaps expected false on reference B580");

        VkFormatProperties3 sampledFormat3 = vkStruct<VkFormatProperties3>(VK_STRUCTURE_TYPE_FORMAT_PROPERTIES_3);
        VkFormatProperties2 sampledFormat2 = vkStruct<VkFormatProperties2>(VK_STRUCTURE_TYPE_FORMAT_PROPERTIES_2);
        sampledFormat2.pNext = &sampledFormat3;
        vkGetPhysicalDeviceFormatProperties2(physical, VK_FORMAT_R8G8B8A8_UNORM, &sampledFormat2);
        if ((sampledFormat3.optimalTilingFeatures & VK_FORMAT_FEATURE_2_SAMPLED_IMAGE_BIT) == 0 ||
            (sampledFormat3.optimalTilingFeatures & VK_FORMAT_FEATURE_2_TRANSFER_DST_BIT) == 0)
            fail("R8G8B8A8_UNORM lacks sampled-image or transfer-dst support");
        VkFormatProperties3 storageFormat3 = vkStruct<VkFormatProperties3>(VK_STRUCTURE_TYPE_FORMAT_PROPERTIES_3);
        VkFormatProperties2 storageFormat2 = vkStruct<VkFormatProperties2>(VK_STRUCTURE_TYPE_FORMAT_PROPERTIES_2);
        storageFormat2.pNext = &storageFormat3;
        vkGetPhysicalDeviceFormatProperties2(physical, VK_FORMAT_R32_UINT, &storageFormat2);
        if ((storageFormat3.optimalTilingFeatures & VK_FORMAT_FEATURE_2_STORAGE_IMAGE_BIT) == 0 ||
            (storageFormat3.optimalTilingFeatures & VK_FORMAT_FEATURE_2_TRANSFER_SRC_BIT) == 0)
            fail("R32_UINT lacks storage-image or transfer-src support");

        uint32_t queueFamilyCount = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(physical, &queueFamilyCount, nullptr);
        std::vector<VkQueueFamilyProperties> queueFamilies(queueFamilyCount);
        vkGetPhysicalDeviceQueueFamilyProperties(physical, &queueFamilyCount, queueFamilies.data());
        std::optional<uint32_t> queueFamily;
        for (uint32_t i = 0; i < queueFamilyCount; ++i) {
            if (queueFamilies[i].queueFlags & VK_QUEUE_COMPUTE_BIT) {
                queueFamily = i;
                break;
            }
        }
        if (!queueFamily)
            fail("selected B580 exposes no compute-capable queue family");

        float queuePriority = 1.0f;
        VkDeviceQueueCreateInfo queueInfo = vkStruct<VkDeviceQueueCreateInfo>(VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO);
        queueInfo.queueFamilyIndex = *queueFamily;
        queueInfo.queueCount = 1;
        queueInfo.pQueuePriorities = &queuePriority;

        // R2 uses only the descriptor-heap binding interface. Untyped pointers are
        // verified as supported above but intentionally not enabled; direct
        // SPV_EXT_descriptor_heap shader access is the separate R3 gate.
        VkPhysicalDeviceDescriptorHeapFeaturesEXT enabledHeap = vkStruct<VkPhysicalDeviceDescriptorHeapFeaturesEXT>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DESCRIPTOR_HEAP_FEATURES_EXT);
        enabledHeap.descriptorHeap = VK_TRUE;
        VkPhysicalDeviceVulkan13Features enabled13 = vkStruct<VkPhysicalDeviceVulkan13Features>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_3_FEATURES);
        enabled13.synchronization2 = VK_TRUE;
        enabledHeap.pNext = &enabled13;
        VkPhysicalDeviceVulkan12Features enabled12 = vkStruct<VkPhysicalDeviceVulkan12Features>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES);
        enabled12.bufferDeviceAddress = VK_TRUE;
        enabled13.pNext = &enabled12;
        VkPhysicalDeviceFeatures2 enabledBase = vkStruct<VkPhysicalDeviceFeatures2>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2);
        enabledBase.features.shaderInt64 = VK_TRUE;
        enabledBase.pNext = &enabledHeap;

        const char* deviceExtensions[] = {VK_EXT_DESCRIPTOR_HEAP_EXTENSION_NAME};
        VkDeviceCreateInfo deviceInfo = vkStruct<VkDeviceCreateInfo>(VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO);
        deviceInfo.pNext = &enabledBase;
        deviceInfo.queueCreateInfoCount = 1;
        deviceInfo.pQueueCreateInfos = &queueInfo;
        deviceInfo.enabledExtensionCount = 1;
        deviceInfo.ppEnabledExtensionNames = deviceExtensions;
        vkCheck(vkCreateDevice(physical, &deviceInfo, nullptr, &device), "vkCreateDevice");

        VkQueue queue = VK_NULL_HANDLE;
        vkGetDeviceQueue(device, *queueFamily, 0, &queue);
        if (!queue)
            fail("vkGetDeviceQueue returned null");

        auto writeSamplers = reinterpret_cast<PFN_vkWriteSamplerDescriptorsEXT>(vkGetDeviceProcAddr(device, "vkWriteSamplerDescriptorsEXT"));
        auto writeResources = reinterpret_cast<PFN_vkWriteResourceDescriptorsEXT>(vkGetDeviceProcAddr(device, "vkWriteResourceDescriptorsEXT"));
        auto bindSamplerHeap = reinterpret_cast<PFN_vkCmdBindSamplerHeapEXT>(vkGetDeviceProcAddr(device, "vkCmdBindSamplerHeapEXT"));
        auto bindResourceHeap = reinterpret_cast<PFN_vkCmdBindResourceHeapEXT>(vkGetDeviceProcAddr(device, "vkCmdBindResourceHeapEXT"));
        auto pushData = reinterpret_cast<PFN_vkCmdPushDataEXT>(vkGetDeviceProcAddr(device, "vkCmdPushDataEXT"));
        auto descriptorSize = reinterpret_cast<PFN_vkGetPhysicalDeviceDescriptorSizeEXT>(vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceDescriptorSizeEXT"));
        if (!writeSamplers || !writeResources || !bindSamplerHeap || !bindResourceHeap || !pushData || !descriptorSize)
            fail("one or more VK_EXT_descriptor_heap entry points are unavailable");

        requireEq(descriptorSize(physical, VK_DESCRIPTOR_TYPE_SAMPLER), heapProps.samplerDescriptorSize, "vkGetPhysicalDeviceDescriptorSizeEXT(SAMPLER)");
        requireEq(descriptorSize(physical, VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE), heapProps.imageDescriptorSize, "vkGetPhysicalDeviceDescriptorSizeEXT(SAMPLED_IMAGE)");
        requireEq(descriptorSize(physical, VK_DESCRIPTOR_TYPE_STORAGE_IMAGE), heapProps.imageDescriptorSize, "vkGetPhysicalDeviceDescriptorSizeEXT(STORAGE_IMAGE)");
        requireEq(descriptorSize(physical, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER), heapProps.bufferDescriptorSize, "vkGetPhysicalDeviceDescriptorSizeEXT(STORAGE_BUFFER)");

        VkPhysicalDeviceMemoryProperties memoryProps{};
        vkGetPhysicalDeviceMemoryProperties(physical, &memoryProps);

        const VkMemoryPropertyFlags heapRequired = VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT;
        const VkMemoryPropertyFlags heapPreferred = VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT;
        const VkDeviceSize samplerTotal = kSamplerUserBytes + heapProps.minSamplerHeapReservedRange + heapProps.samplerHeapAlignment;
        const VkDeviceSize resourceTotal = kResourceUserBytes + heapProps.minResourceHeapReservedRange + heapProps.resourceHeapAlignment;
        samplerHeap = createBuffer(
            device, memoryProps, samplerTotal,
            VK_BUFFER_USAGE_DESCRIPTOR_HEAP_BIT_EXT | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT,
            heapRequired, heapPreferred, true);
        resourceHeap = createBuffer(
            device, memoryProps, resourceTotal,
            VK_BUFFER_USAGE_DESCRIPTOR_HEAP_BIT_EXT | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT,
            heapRequired, heapPreferred, true);
        if (!samplerHeap.mapped || !resourceHeap.mapped)
            fail("descriptor heaps are not directly mapped");

        const VkDeviceAddress samplerBase = alignUp(samplerHeap.address, heapProps.samplerHeapAlignment);
        const VkDeviceAddress resourceBase = alignUp(resourceHeap.address, heapProps.resourceHeapAlignment);
        const VkDeviceSize samplerDelta = samplerBase - samplerHeap.address;
        const VkDeviceSize resourceDelta = resourceBase - resourceHeap.address;
        const VkDeviceSize samplerRangeSize = kSamplerUserBytes + heapProps.minSamplerHeapReservedRange;
        const VkDeviceSize resourceRangeSize = kResourceUserBytes + heapProps.minResourceHeapReservedRange;
        if (samplerDelta + samplerRangeSize > samplerHeap.size || resourceDelta + resourceRangeSize > resourceHeap.size)
            fail("aligned descriptor heap range escaped its backing buffer");

        auto* samplerHost = static_cast<uint8_t*>(samplerHeap.mapped) + samplerDelta;
        auto* resourceHost = static_cast<uint8_t*>(resourceHeap.mapped) + resourceDelta;
        std::memset(samplerHost, 0, static_cast<size_t>(samplerRangeSize));
        std::memset(resourceHost, 0, static_cast<size_t>(resourceRangeSize));

        const VkDeviceSize unifiedResourceStride = std::max(heapProps.imageDescriptorSize, heapProps.bufferDescriptorSize);
        requireEq(unifiedResourceStride, 64, "unified resource stride");
        const VkDeviceSize sampledOffset = 0;
        const VkDeviceSize storageImageOffset = unifiedResourceStride;
        const VkDeviceSize storageBufferOffset = unifiedResourceStride * 2;
        if ((sampledOffset % heapProps.imageDescriptorAlignment) != 0 ||
            (storageImageOffset % heapProps.imageDescriptorAlignment) != 0 ||
            (storageBufferOffset % heapProps.bufferDescriptorAlignment) != 0)
            fail("fixture resource heap offsets violate descriptor alignment");

        staging = createBuffer(
            device, memoryProps, 8, VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
            VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT, false);
        words = createBuffer(
            device, memoryProps, 16,
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
            VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT, true);
        readback = createBuffer(
            device, memoryProps, 16, VK_BUFFER_USAGE_TRANSFER_DST_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
            0, false);
        if (!staging.mapped || !words.mapped || !readback.mapped)
            fail("host-visible fixture buffers were not mapped");

        const std::array<uint8_t, 4> colorA{32, 64, 96, 128};
        const std::array<uint8_t, 4> colorB{200, 100, 50, 240};
        std::memcpy(staging.mapped, colorA.data(), colorA.size());
        std::memcpy(static_cast<uint8_t*>(staging.mapped) + 4, colorB.data(), colorB.size());
        std::memset(words.mapped, 0, 16);
        std::memset(readback.mapped, 0, 16);

        sourceA = createImage(device, memoryProps, VK_FORMAT_R8G8B8A8_UNORM,
                              VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT);
        sourceB = createImage(device, memoryProps, VK_FORMAT_R8G8B8A8_UNORM,
                              VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT);
        output = createImage(device, memoryProps, VK_FORMAT_R32_UINT,
                             VK_IMAGE_USAGE_STORAGE_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT);

        VkCommandPoolCreateInfo poolInfo = vkStruct<VkCommandPoolCreateInfo>(VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
        poolInfo.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        poolInfo.queueFamilyIndex = *queueFamily;
        vkCheck(vkCreateCommandPool(device, &poolInfo, nullptr, &commandPool), "vkCreateCommandPool");
        VkCommandBufferAllocateInfo commandAlloc = vkStruct<VkCommandBufferAllocateInfo>(VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
        commandAlloc.commandPool = commandPool;
        commandAlloc.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        commandAlloc.commandBufferCount = 1;
        vkCheck(vkAllocateCommandBuffers(device, &commandAlloc, &commandBuffer), "vkAllocateCommandBuffers");

        beginCommand(commandBuffer);

        VkMemoryBarrier2 stagingHostToTransfer = vkStruct<VkMemoryBarrier2>(VK_STRUCTURE_TYPE_MEMORY_BARRIER_2);
        stagingHostToTransfer.srcStageMask = VK_PIPELINE_STAGE_2_HOST_BIT;
        stagingHostToTransfer.srcAccessMask = VK_ACCESS_2_HOST_WRITE_BIT;
        stagingHostToTransfer.dstStageMask = VK_PIPELINE_STAGE_2_TRANSFER_BIT;
        stagingHostToTransfer.dstAccessMask = VK_ACCESS_2_TRANSFER_READ_BIT;
        VkDependencyInfo stagingHostToTransferDep = vkStruct<VkDependencyInfo>(VK_STRUCTURE_TYPE_DEPENDENCY_INFO);
        stagingHostToTransferDep.memoryBarrierCount = 1;
        stagingHostToTransferDep.pMemoryBarriers = &stagingHostToTransfer;
        vkCmdPipelineBarrier2(commandBuffer, &stagingHostToTransferDep);

        imageBarrier(commandBuffer, sourceA.image, VK_PIPELINE_STAGE_2_NONE, 0,
                     VK_PIPELINE_STAGE_2_TRANSFER_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                     VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);
        imageBarrier(commandBuffer, sourceB.image, VK_PIPELINE_STAGE_2_NONE, 0,
                     VK_PIPELINE_STAGE_2_TRANSFER_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                     VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);
        imageBarrier(commandBuffer, output.image, VK_PIPELINE_STAGE_2_NONE, 0,
                     VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_WRITE_BIT,
                     VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL);

        VkBufferImageCopy copyA{};
        copyA.bufferOffset = 0;
        copyA.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        copyA.imageSubresource.layerCount = 1;
        copyA.imageExtent = {1, 1, 1};
        vkCmdCopyBufferToImage(commandBuffer, staging.buffer, sourceA.image,
                               VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &copyA);
        VkBufferImageCopy copyB = copyA;
        copyB.bufferOffset = 4;
        vkCmdCopyBufferToImage(commandBuffer, staging.buffer, sourceB.image,
                               VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &copyB);

        imageBarrier(commandBuffer, sourceA.image, VK_PIPELINE_STAGE_2_TRANSFER_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                     VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_READ_BIT,
                     VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL);
        imageBarrier(commandBuffer, sourceB.image, VK_PIPELINE_STAGE_2_TRANSFER_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                     VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_READ_BIT,
                     VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL);
        vkCheck(vkEndCommandBuffer(commandBuffer), "vkEndCommandBuffer(upload)");
        submitAndWait(device, queue, commandBuffer);
        vkCheck(vkResetCommandBuffer(commandBuffer, 0), "vkResetCommandBuffer(after upload)");

        VkShaderModuleCreateInfo shaderInfo = vkStruct<VkShaderModuleCreateInfo>(VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO);
        shaderInfo.codeSize = spirv.size() * sizeof(uint32_t);
        shaderInfo.pCode = spirv.data();
        vkCheck(vkCreateShaderModule(device, &shaderInfo, nullptr, &shaderModule), "vkCreateShaderModule");

        std::array<VkDescriptorSetAndBindingMappingEXT, 4> mappings{};
        auto makeMapping = [](uint32_t binding, VkSpirvResourceTypeFlagsEXT mask, uint32_t heapOffset) {
            VkDescriptorSetAndBindingMappingEXT mapping = vkStruct<VkDescriptorSetAndBindingMappingEXT>(VK_STRUCTURE_TYPE_DESCRIPTOR_SET_AND_BINDING_MAPPING_EXT);
            mapping.descriptorSet = 0;
            mapping.firstBinding = binding;
            mapping.bindingCount = 1;
            mapping.resourceMask = mask;
            mapping.source = VK_DESCRIPTOR_MAPPING_SOURCE_HEAP_WITH_CONSTANT_OFFSET_EXT;
            mapping.sourceData.constantOffset.heapOffset = heapOffset;
            mapping.sourceData.constantOffset.heapArrayStride = 0;
            mapping.sourceData.constantOffset.pEmbeddedSampler = nullptr;
            mapping.sourceData.constantOffset.samplerHeapOffset = 0;
            mapping.sourceData.constantOffset.samplerHeapArrayStride = 0;
            return mapping;
        };
        mappings[0] = makeMapping(0, VK_SPIRV_RESOURCE_TYPE_SAMPLED_IMAGE_BIT_EXT, static_cast<uint32_t>(sampledOffset));
        mappings[1] = makeMapping(1, VK_SPIRV_RESOURCE_TYPE_SAMPLER_BIT_EXT, 0);
        mappings[2] = makeMapping(2, VK_SPIRV_RESOURCE_TYPE_READ_WRITE_IMAGE_BIT_EXT, static_cast<uint32_t>(storageImageOffset));
        mappings[3] = makeMapping(3, VK_SPIRV_RESOURCE_TYPE_READ_WRITE_STORAGE_BUFFER_BIT_EXT, static_cast<uint32_t>(storageBufferOffset));

        VkShaderDescriptorSetAndBindingMappingInfoEXT mappingInfo = vkStruct<VkShaderDescriptorSetAndBindingMappingInfoEXT>(VK_STRUCTURE_TYPE_SHADER_DESCRIPTOR_SET_AND_BINDING_MAPPING_INFO_EXT);
        mappingInfo.mappingCount = static_cast<uint32_t>(mappings.size());
        mappingInfo.pMappings = mappings.data();

        VkPipelineShaderStageCreateInfo stageInfo = vkStruct<VkPipelineShaderStageCreateInfo>(VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO);
        stageInfo.pNext = &mappingInfo;
        stageInfo.stage = VK_SHADER_STAGE_COMPUTE_BIT;
        stageInfo.module = shaderModule;
        stageInfo.pName = "computeMain";

        VkPipelineCreateFlags2CreateInfo flags2 = vkStruct<VkPipelineCreateFlags2CreateInfo>(VK_STRUCTURE_TYPE_PIPELINE_CREATE_FLAGS_2_CREATE_INFO);
        flags2.flags = VK_PIPELINE_CREATE_2_DESCRIPTOR_HEAP_BIT_EXT;
        VkComputePipelineCreateInfo pipelineInfo = vkStruct<VkComputePipelineCreateInfo>(VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO);
        pipelineInfo.pNext = &flags2;
        pipelineInfo.stage = stageInfo;
        pipelineInfo.layout = VK_NULL_HANDLE;
        vkCheck(vkCreateComputePipelines(device, VK_NULL_HANDLE, 1, &pipelineInfo, nullptr, &pipeline), "vkCreateComputePipelines");

        VkBindHeapInfoEXT samplerBind = vkStruct<VkBindHeapInfoEXT>(VK_STRUCTURE_TYPE_BIND_HEAP_INFO_EXT);
        samplerBind.heapRange.address = samplerBase;
        samplerBind.heapRange.size = samplerRangeSize;
        samplerBind.reservedRangeOffset = kSamplerUserBytes;
        samplerBind.reservedRangeSize = heapProps.minSamplerHeapReservedRange;

        VkBindHeapInfoEXT resourceBind = vkStruct<VkBindHeapInfoEXT>(VK_STRUCTURE_TYPE_BIND_HEAP_INFO_EXT);
        resourceBind.heapRange.address = resourceBase;
        resourceBind.heapRange.size = resourceRangeSize;
        resourceBind.reservedRangeOffset = kResourceUserBytes;
        resourceBind.reservedRangeSize = heapProps.minResourceHeapReservedRange;

        VkSamplerCreateInfo samplerInfo = vkStruct<VkSamplerCreateInfo>(VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO);
        samplerInfo.magFilter = VK_FILTER_NEAREST;
        samplerInfo.minFilter = VK_FILTER_NEAREST;
        samplerInfo.mipmapMode = VK_SAMPLER_MIPMAP_MODE_NEAREST;
        samplerInfo.addressModeU = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
        samplerInfo.addressModeV = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
        samplerInfo.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
        samplerInfo.minLod = 0.0f;
        samplerInfo.maxLod = 0.0f;
        samplerInfo.maxAnisotropy = 1.0f;
        samplerInfo.borderColor = VK_BORDER_COLOR_FLOAT_TRANSPARENT_BLACK;

        uint64_t traceHash = 1469598103934665603ull;
        uint32_t expectedAccum = 0;
        const std::array<std::array<uint8_t, 4>, 2> colors{colorA, colorB};

        for (uint32_t iteration = 0; iteration < args.iterations; ++iteration) {
            const uint32_t sourceIndex = iteration & 1u;
            const auto& sourceColor = colors[sourceIndex];
            VkImage sourceImage = sourceIndex == 0 ? sourceA.image : sourceB.image;

            VkImageViewCreateInfo sampledView = imageViewInfo(sourceImage, VK_FORMAT_R8G8B8A8_UNORM);
            VkImageDescriptorInfoEXT sampledImageInfo = vkStruct<VkImageDescriptorInfoEXT>(VK_STRUCTURE_TYPE_IMAGE_DESCRIPTOR_INFO_EXT);
            sampledImageInfo.pView = &sampledView;
            sampledImageInfo.layout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
            VkResourceDescriptorInfoEXT sampledResource = vkStruct<VkResourceDescriptorInfoEXT>(VK_STRUCTURE_TYPE_RESOURCE_DESCRIPTOR_INFO_EXT);
            sampledResource.type = VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE;
            sampledResource.data.pImage = &sampledImageInfo;
            VkHostAddressRangeEXT sampledRange{
                resourceHost + sampledOffset,
                static_cast<size_t>(heapProps.imageDescriptorSize),
            };
            vkCheck(writeResources(device, 1, &sampledResource, &sampledRange), "vkWriteResourceDescriptorsEXT(sampled image)");

            VkImageViewCreateInfo storageView = imageViewInfo(output.image, VK_FORMAT_R32_UINT);
            VkImageDescriptorInfoEXT storageImageInfo = vkStruct<VkImageDescriptorInfoEXT>(VK_STRUCTURE_TYPE_IMAGE_DESCRIPTOR_INFO_EXT);
            storageImageInfo.pView = &storageView;
            storageImageInfo.layout = VK_IMAGE_LAYOUT_GENERAL;
            VkResourceDescriptorInfoEXT storageResource = vkStruct<VkResourceDescriptorInfoEXT>(VK_STRUCTURE_TYPE_RESOURCE_DESCRIPTOR_INFO_EXT);
            storageResource.type = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE;
            storageResource.data.pImage = &storageImageInfo;
            VkHostAddressRangeEXT storageRange{
                resourceHost + storageImageOffset,
                static_cast<size_t>(heapProps.imageDescriptorSize),
            };
            vkCheck(writeResources(device, 1, &storageResource, &storageRange), "vkWriteResourceDescriptorsEXT(storage image)");

            VkDeviceAddressRangeEXT wordsAddressRange{};
            wordsAddressRange.address = words.address;
            wordsAddressRange.size = words.size;
            VkResourceDescriptorInfoEXT wordsResource = vkStruct<VkResourceDescriptorInfoEXT>(VK_STRUCTURE_TYPE_RESOURCE_DESCRIPTOR_INFO_EXT);
            wordsResource.type = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            wordsResource.data.pAddressRange = &wordsAddressRange;
            VkHostAddressRangeEXT wordsDescriptorRange{
                resourceHost + storageBufferOffset,
                static_cast<size_t>(heapProps.bufferDescriptorSize),
            };
            vkCheck(writeResources(device, 1, &wordsResource, &wordsDescriptorRange), "vkWriteResourceDescriptorsEXT(storage buffer)");

            VkHostAddressRangeEXT samplerRange{
                samplerHost,
                static_cast<size_t>(heapProps.samplerDescriptorSize),
            };
            vkCheck(writeSamplers(device, 1, &samplerInfo, &samplerRange), "vkWriteSamplerDescriptorsEXT");

            GpuShaderRoot root{};
            root.sceneRootAddress = 0x1111111111111111ull;
            root.frameConstantsAddress = 0x2222222222222222ull;
            root.viewConstantsAddress = 0x3333333333333333ull;
            root.passDataAddress = static_cast<uint64_t>((iteration % 63u) + 1u);
            const uint32_t delta = static_cast<uint32_t>(root.passDataAddress & 0xffu);
            const std::array<uint32_t, 4> expected{
                static_cast<uint32_t>(sourceColor[0]) + delta,
                static_cast<uint32_t>(sourceColor[1]) + delta * 2u,
                static_cast<uint32_t>(sourceColor[2]) + delta * 3u,
                static_cast<uint32_t>(sourceColor[3]) + delta * 4u,
            };
            expectedAccum += expected[0];

            vkCheck(vkResetCommandBuffer(commandBuffer, 0), "vkResetCommandBuffer(iteration)");
            beginCommand(commandBuffer);

            VkMemoryBarrier2 hostToHeap = vkStruct<VkMemoryBarrier2>(VK_STRUCTURE_TYPE_MEMORY_BARRIER_2);
            hostToHeap.srcStageMask = VK_PIPELINE_STAGE_2_HOST_BIT;
            hostToHeap.srcAccessMask = VK_ACCESS_2_HOST_WRITE_BIT;
            hostToHeap.dstStageMask = VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT;
            hostToHeap.dstAccessMask = VK_ACCESS_2_RESOURCE_HEAP_READ_BIT_EXT | VK_ACCESS_2_SAMPLER_HEAP_READ_BIT_EXT | VK_ACCESS_2_SHADER_READ_BIT;
            VkDependencyInfo hostToHeapDep = vkStruct<VkDependencyInfo>(VK_STRUCTURE_TYPE_DEPENDENCY_INFO);
            hostToHeapDep.memoryBarrierCount = 1;
            hostToHeapDep.pMemoryBarriers = &hostToHeap;
            vkCmdPipelineBarrier2(commandBuffer, &hostToHeapDep);

            vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline);
            bindSamplerHeap(commandBuffer, &samplerBind);
            bindResourceHeap(commandBuffer, &resourceBind);
            VkPushDataInfoEXT pushInfo = vkStruct<VkPushDataInfoEXT>(VK_STRUCTURE_TYPE_PUSH_DATA_INFO_EXT);
            pushInfo.offset = 0;
            pushInfo.data.address = &root;
            pushInfo.data.size = sizeof(root);
            pushData(commandBuffer, &pushInfo);
            vkCmdDispatch(commandBuffer, 1, 1, 1);

            VkImageMemoryBarrier2 outputToTransfer = vkStruct<VkImageMemoryBarrier2>(VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER_2);
            outputToTransfer.srcStageMask = VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT;
            outputToTransfer.srcAccessMask = VK_ACCESS_2_SHADER_WRITE_BIT;
            outputToTransfer.dstStageMask = VK_PIPELINE_STAGE_2_TRANSFER_BIT;
            outputToTransfer.dstAccessMask = VK_ACCESS_2_TRANSFER_READ_BIT;
            outputToTransfer.oldLayout = VK_IMAGE_LAYOUT_GENERAL;
            outputToTransfer.newLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
            outputToTransfer.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            outputToTransfer.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            outputToTransfer.image = output.image;
            outputToTransfer.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            outputToTransfer.subresourceRange.levelCount = 1;
            outputToTransfer.subresourceRange.layerCount = 1;

            VkMemoryBarrier2 wordsToHost = vkStruct<VkMemoryBarrier2>(VK_STRUCTURE_TYPE_MEMORY_BARRIER_2);
            wordsToHost.srcStageMask = VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT;
            wordsToHost.srcAccessMask = VK_ACCESS_2_SHADER_WRITE_BIT;
            wordsToHost.dstStageMask = VK_PIPELINE_STAGE_2_HOST_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT;
            wordsToHost.dstAccessMask = VK_ACCESS_2_HOST_READ_BIT | VK_ACCESS_2_SHADER_READ_BIT;

            VkDependencyInfo postDispatch = vkStruct<VkDependencyInfo>(VK_STRUCTURE_TYPE_DEPENDENCY_INFO);
            postDispatch.memoryBarrierCount = 1;
            postDispatch.pMemoryBarriers = &wordsToHost;
            postDispatch.imageMemoryBarrierCount = 1;
            postDispatch.pImageMemoryBarriers = &outputToTransfer;
            vkCmdPipelineBarrier2(commandBuffer, &postDispatch);

            VkBufferImageCopy imageCopy{};
            imageCopy.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            imageCopy.imageSubresource.layerCount = 1;
            imageCopy.imageExtent = {1, 1, 1};
            vkCmdCopyImageToBuffer(commandBuffer, output.image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                                   readback.buffer, 1, &imageCopy);

            VkImageMemoryBarrier2 outputBack = vkStruct<VkImageMemoryBarrier2>(VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER_2);
            outputBack.srcStageMask = VK_PIPELINE_STAGE_2_TRANSFER_BIT;
            outputBack.srcAccessMask = VK_ACCESS_2_TRANSFER_READ_BIT;
            outputBack.dstStageMask = VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT;
            outputBack.dstAccessMask = VK_ACCESS_2_SHADER_WRITE_BIT;
            outputBack.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
            outputBack.newLayout = VK_IMAGE_LAYOUT_GENERAL;
            outputBack.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            outputBack.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            outputBack.image = output.image;
            outputBack.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            outputBack.subresourceRange.levelCount = 1;
            outputBack.subresourceRange.layerCount = 1;

            VkMemoryBarrier2 readbackToHost = vkStruct<VkMemoryBarrier2>(VK_STRUCTURE_TYPE_MEMORY_BARRIER_2);
            readbackToHost.srcStageMask = VK_PIPELINE_STAGE_2_TRANSFER_BIT;
            readbackToHost.srcAccessMask = VK_ACCESS_2_TRANSFER_WRITE_BIT;
            readbackToHost.dstStageMask = VK_PIPELINE_STAGE_2_HOST_BIT;
            readbackToHost.dstAccessMask = VK_ACCESS_2_HOST_READ_BIT;

            VkDependencyInfo postCopy = vkStruct<VkDependencyInfo>(VK_STRUCTURE_TYPE_DEPENDENCY_INFO);
            postCopy.memoryBarrierCount = 1;
            postCopy.pMemoryBarriers = &readbackToHost;
            postCopy.imageMemoryBarrierCount = 1;
            postCopy.pImageMemoryBarriers = &outputBack;
            vkCmdPipelineBarrier2(commandBuffer, &postCopy);

            vkCheck(vkEndCommandBuffer(commandBuffer), "vkEndCommandBuffer(iteration)");
            submitAndWait(device, queue, commandBuffer);

            uint32_t actualPixel = 0;
            std::array<uint32_t, 4> actualWords{};
            std::memcpy(&actualPixel, readback.mapped, sizeof(actualPixel));
            std::memcpy(actualWords.data(), words.mapped, sizeof(actualWords));
            if (actualPixel != expected[0]) {
                std::ostringstream out;
                out << "storage-image readback mismatch at iteration " << iteration;
                fail(out.str());
            }
            if (actualWords[0] != expectedAccum || actualWords[1] != expected[1] ||
                actualWords[2] != expected[2] || actualWords[3] != expected[3]) {
                std::ostringstream out;
                out << "storage-buffer read/write mismatch at iteration " << iteration;
                fail(out.str());
            }

            traceHash = fnv1a(traceHash, iteration);
            traceHash = fnv1a(traceHash, sourceIndex);
            traceHash = fnv1a(traceHash, delta);
            traceHash = fnv1a(traceHash, expectedAccum);
            for (uint32_t value : expected)
                traceHash = fnv1a(traceHash, value);
        }

        vkDeviceWaitIdle(device);
        if (validation.errors != 0 || validation.warnings != 0) {
            std::ostringstream out;
            out << "validation layer reported " << validation.errors << " errors and "
                << validation.warnings << " warnings";
            fail(out.str());
        }

        std::cout << "fixture.schema=1\n";
        std::cout << "compile.vulkan_header_version=" << VK_HEADER_VERSION << '\n';
        std::cout << "runtime.loader_api=" << apiVersionString(loaderVersion) << '\n';
        std::cout << "validation.layer_spec=" << apiVersionString(validationLayer.specVersion) << '\n';
        std::cout << "validation.layer_impl=" << validationLayer.implementationVersion << '\n';
        std::cout << "device.name=" << baseProps.deviceName << '\n';
        std::cout << "device.vendor_id=0x" << std::hex << std::setw(4) << std::setfill('0') << baseProps.vendorID << std::dec << '\n';
        std::cout << "device.device_id=0x" << std::hex << std::setw(4) << std::setfill('0') << baseProps.deviceID << std::dec << '\n';
        std::cout << "device.api=" << apiVersionString(baseProps.apiVersion) << '\n';
        std::cout << "device.driver_version=" << baseProps.driverVersion << '\n';
        std::cout << "device.driver_id=" << static_cast<uint32_t>(driverProps.driverID) << '\n';
        std::cout << "device.driver_name=" << driverProps.driverName << '\n';
        std::cout << "device.driver_info=" << driverProps.driverInfo << '\n';
        std::cout << "device.device_uuid=" << hexBytes(idProps.deviceUUID, VK_UUID_SIZE) << '\n';
        std::cout << "device.driver_uuid=" << hexBytes(idProps.driverUUID, VK_UUID_SIZE) << '\n';
        std::cout << "device.pipeline_cache_uuid=" << hexBytes(baseProps.pipelineCacheUUID, VK_UUID_SIZE) << '\n';
        std::cout << "extension.descriptor_heap_revision=" << descriptorHeapRevision << '\n';
        std::cout << "feature.descriptor_heap=true\n";
        std::cout << "feature.descriptor_heap_capture_replay=true\n";
        std::cout << "feature.shader_untyped_pointers=true\n";
        std::cout << "feature.buffer_device_address=true\n";
        std::cout << "heap.sampler_alignment=" << heapProps.samplerHeapAlignment << '\n';
        std::cout << "heap.resource_alignment=" << heapProps.resourceHeapAlignment << '\n';
        std::cout << "heap.max_sampler_size=" << heapProps.maxSamplerHeapSize << '\n';
        std::cout << "heap.max_resource_size=" << heapProps.maxResourceHeapSize << '\n';
        std::cout << "heap.sampler_descriptor_size=" << heapProps.samplerDescriptorSize << '\n';
        std::cout << "heap.image_descriptor_size=" << heapProps.imageDescriptorSize << '\n';
        std::cout << "heap.buffer_descriptor_size=" << heapProps.bufferDescriptorSize << '\n';
        std::cout << "heap.sampler_descriptor_alignment=" << heapProps.samplerDescriptorAlignment << '\n';
        std::cout << "heap.image_descriptor_alignment=" << heapProps.imageDescriptorAlignment << '\n';
        std::cout << "heap.buffer_descriptor_alignment=" << heapProps.bufferDescriptorAlignment << '\n';
        std::cout << "heap.max_push_data_size=" << heapProps.maxPushDataSize << '\n';
        std::cout << "heap.sparse=true\n";
        std::cout << "heap.protected=false\n";
        std::cout << "heap.direct_mapped=true\n";
        std::cout << "heap.sampler_memory_device_local="
                  << ((samplerHeap.memoryFlags & VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT) ? "true" : "false") << '\n';
        std::cout << "heap.resource_memory_device_local="
                  << ((resourceHeap.memoryFlags & VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT) ? "true" : "false") << '\n';
        std::cout << "heap.explicit_subrange_alignment=PASS\n";
        std::cout << "heap.reserved_tail_policy=PASS\n";
        std::cout << "execution.sampler_descriptor_write=PASS\n";
        std::cout << "execution.resource_descriptor_write=PASS\n";
        std::cout << "execution.sampler_heap_bind=PASS\n";
        std::cout << "execution.resource_heap_bind=PASS\n";
        std::cout << "execution.push_data_32_bytes=PASS\n";
        std::cout << "execution.sampled_image_read=PASS\n";
        std::cout << "execution.storage_image_write_readback=PASS\n";
        std::cout << "execution.storage_buffer_read_write=PASS\n";
        std::cout << "churn.iterations=" << args.iterations << '\n';
        std::cout << "churn.retire_before_republish=fence-complete\n";
        std::cout << "trace.fnv1a64=" << hex64(traceHash) << '\n';
        std::cout << "validation.warning_count=0\n";
        std::cout << "validation.error_count=0\n";
        std::cout << "result=PASS\n";

        vkDestroyPipeline(device, pipeline, nullptr);
        pipeline = VK_NULL_HANDLE;
        vkDestroyShaderModule(device, shaderModule, nullptr);
        shaderModule = VK_NULL_HANDLE;
        destroyImage(device, output);
        destroyImage(device, sourceB);
        destroyImage(device, sourceA);
        destroyBuffer(device, readback);
        destroyBuffer(device, words);
        destroyBuffer(device, staging);
        destroyBuffer(device, resourceHeap);
        destroyBuffer(device, samplerHeap);
        vkDestroyCommandPool(device, commandPool, nullptr);
        commandPool = VK_NULL_HANDLE;
        vkDestroyDevice(device, nullptr);
        device = VK_NULL_HANDLE;
        destroyDebug(instance, messenger, nullptr);
        messenger = VK_NULL_HANDLE;
        vkDestroyInstance(instance, nullptr);
        instance = VK_NULL_HANDLE;
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "M0.7 descriptor-heap fixture: FAIL: " << e.what() << '\n';
        if (device)
            vkDeviceWaitIdle(device);
        if (device && pipeline)
            vkDestroyPipeline(device, pipeline, nullptr);
        if (device && shaderModule)
            vkDestroyShaderModule(device, shaderModule, nullptr);
        if (device) {
            destroyImage(device, output);
            destroyImage(device, sourceB);
            destroyImage(device, sourceA);
            destroyBuffer(device, readback);
            destroyBuffer(device, words);
            destroyBuffer(device, staging);
            destroyBuffer(device, resourceHeap);
            destroyBuffer(device, samplerHeap);
            if (commandPool)
                vkDestroyCommandPool(device, commandPool, nullptr);
            vkDestroyDevice(device, nullptr);
        }
        if (instance && messenger) {
            if (auto destroyDebug = reinterpret_cast<PFN_vkDestroyDebugUtilsMessengerEXT>(
                    vkGetInstanceProcAddr(instance, "vkDestroyDebugUtilsMessengerEXT")))
                destroyDebug(instance, messenger, nullptr);
        }
        if (instance)
            vkDestroyInstance(instance, nullptr);
        return 1;
    }
}
