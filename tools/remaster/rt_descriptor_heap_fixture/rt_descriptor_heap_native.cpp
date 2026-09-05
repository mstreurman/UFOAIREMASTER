#include <vulkan/vulkan.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
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
constexpr uint32_t kHitMagic = 0xC0FFEE42u;
constexpr VkDeviceSize kApplicationHeapBytes = 4096;
constexpr VkDeviceSize kAsByteOffset = 128;
constexpr VkDeviceSize kOutputByteOffset = 256;

struct GpuShaderRoot {
    uint64_t sceneRootAddress;
    uint64_t frameConstantsAddress;
    uint64_t viewConstantsAddress;
    uint64_t passDataAddress;
};
static_assert(sizeof(GpuShaderRoot) == 32);

struct Args {
    std::string raygen;
    std::string miss;
    std::string closestHit;
};

[[noreturn]] void fail(const std::string& message) { throw std::runtime_error(message); }

void vkCheck(VkResult result, std::string_view what) {
    if (result != VK_SUCCESS) {
        std::ostringstream out;
        out << what << " failed with VkResult " << static_cast<int>(result);
        fail(out.str());
    }
}

template <typename T>
T vkStruct(VkStructureType sType) {
    T out{};
    out.sType = sType;
    return out;
}

VkDeviceAddress alignUp(VkDeviceAddress value, VkDeviceSize alignment) {
    if (alignment == 0 || (alignment & (alignment - 1)) != 0)
        fail("alignment is not a non-zero power of two");
    return (value + alignment - 1) & ~(alignment - 1);
}

std::string hexAddress(VkDeviceAddress value) {
    std::ostringstream out;
    out << "0x" << std::hex << std::setfill('0') << std::setw(16) << value;
    return out.str();
}

std::string apiVersionString(uint32_t version) {
    std::ostringstream out;
    out << VK_API_VERSION_MAJOR(version) << '.' << VK_API_VERSION_MINOR(version) << '.'
        << VK_API_VERSION_PATCH(version);
    return out.str();
}

Args parseArgs(int argc, char** argv) {
    Args out;
    for (int i = 1; i < argc; ++i) {
        const std::string_view arg(argv[i]);
        auto take = [&](std::string& dst) {
            if (++i >= argc)
                fail("missing argument value");
            dst = argv[i];
        };
        if (arg == "--raygen") take(out.raygen);
        else if (arg == "--miss") take(out.miss);
        else if (arg == "--closest-hit") take(out.closestHit);
        else fail("unknown argument: " + std::string(arg));
    }
    if (out.raygen.empty() || out.miss.empty() || out.closestHit.empty())
        fail("usage: --raygen FILE --miss FILE --closest-hit FILE");
    return out;
}

std::vector<uint32_t> readSpirv(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file)
        fail("cannot open SPIR-V: " + path);
    const std::streamsize bytes = file.tellg();
    if (bytes <= 0 || (bytes % 4) != 0)
        fail("invalid SPIR-V byte size: " + path);
    file.seekg(0, std::ios::beg);
    std::vector<uint32_t> words(static_cast<size_t>(bytes / 4));
    if (!file.read(reinterpret_cast<char*>(words.data()), bytes))
        fail("cannot read SPIR-V: " + path);
    return words;
}

struct ValidationState { uint32_t warnings = 0; uint32_t errors = 0; };

VKAPI_ATTR VkBool32 VKAPI_CALL validationCallback(
    VkDebugUtilsMessageSeverityFlagBitsEXT severity,
    VkDebugUtilsMessageTypeFlagsEXT,
    const VkDebugUtilsMessengerCallbackDataEXT* data,
    void* userData) {
    auto* state = static_cast<ValidationState*>(userData);
    if (severity & VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT) ++state->errors;
    else if (severity & VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT) ++state->warnings;
    std::cerr << "[validation] " << (data && data->pMessage ? data->pMessage : "(no message)") << '\n';
    return VK_FALSE;
}

bool hasExtension(const std::vector<VkExtensionProperties>& exts, const char* name) {
    for (const auto& ext : exts)
        if (std::strcmp(ext.extensionName, name) == 0) return true;
    return false;
}

bool hasLayer(const std::vector<VkLayerProperties>& layers, const char* name) {
    for (const auto& layer : layers)
        if (std::strcmp(layer.layerName, name) == 0) return true;
    return false;
}

uint32_t chooseMemoryType(
    const VkPhysicalDeviceMemoryProperties& props,
    uint32_t bits,
    VkMemoryPropertyFlags required,
    VkMemoryPropertyFlags preferred,
    VkMemoryPropertyFlags* selected = nullptr) {
    std::optional<uint32_t> fallback;
    for (uint32_t i = 0; i < props.memoryTypeCount; ++i) {
        if ((bits & (1u << i)) == 0) continue;
        const auto flags = props.memoryTypes[i].propertyFlags;
        if ((flags & required) != required) continue;
        if ((flags & preferred) == preferred) {
            if (selected) *selected = flags;
            return i;
        }
        if (!fallback) fallback = i;
    }
    if (fallback) {
        if (selected) *selected = props.memoryTypes[*fallback].propertyFlags;
        return *fallback;
    }
    fail("no compatible memory type");
}

struct Buffer {
    VkBuffer buffer = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    VkDeviceSize size = 0;
    VkDeviceAddress address = 0;
    void* mapped = nullptr;
    VkMemoryPropertyFlags flags = 0;
};

Buffer createBuffer(
    VkDevice device,
    const VkPhysicalDeviceMemoryProperties& memoryProps,
    VkDeviceSize size,
    VkBufferUsageFlags usage,
    VkMemoryPropertyFlags required,
    VkMemoryPropertyFlags preferred,
    bool deviceAddress) {
    Buffer out{};
    out.size = size;
    VkBufferCreateInfo ci = vkStruct<VkBufferCreateInfo>(VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO);
    ci.size = size;
    ci.usage = usage;
    ci.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    vkCheck(vkCreateBuffer(device, &ci, nullptr, &out.buffer), "vkCreateBuffer");

    VkMemoryRequirements req{};
    vkGetBufferMemoryRequirements(device, out.buffer, &req);
    VkMemoryAllocateFlagsInfo flagsInfo = vkStruct<VkMemoryAllocateFlagsInfo>(VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_FLAGS_INFO);
    flagsInfo.flags = deviceAddress ? VK_MEMORY_ALLOCATE_DEVICE_ADDRESS_BIT : 0;
    VkMemoryAllocateInfo ai = vkStruct<VkMemoryAllocateInfo>(VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO);
    ai.pNext = deviceAddress ? &flagsInfo : nullptr;
    ai.allocationSize = req.size;
    ai.memoryTypeIndex = chooseMemoryType(memoryProps, req.memoryTypeBits, required, preferred, &out.flags);
    vkCheck(vkAllocateMemory(device, &ai, nullptr, &out.memory), "vkAllocateMemory");
    vkCheck(vkBindBufferMemory(device, out.buffer, out.memory, 0), "vkBindBufferMemory");
    if (out.flags & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT)
        vkCheck(vkMapMemory(device, out.memory, 0, VK_WHOLE_SIZE, 0, &out.mapped), "vkMapMemory");
    if (deviceAddress) {
        VkBufferDeviceAddressInfo bi = vkStruct<VkBufferDeviceAddressInfo>(VK_STRUCTURE_TYPE_BUFFER_DEVICE_ADDRESS_INFO);
        bi.buffer = out.buffer;
        out.address = vkGetBufferDeviceAddress(device, &bi);
        if (!out.address) fail("vkGetBufferDeviceAddress returned zero");
    }
    return out;
}

void destroyBuffer(VkDevice device, Buffer& buffer) {
    if (buffer.mapped) vkUnmapMemory(device, buffer.memory);
    if (buffer.buffer) vkDestroyBuffer(device, buffer.buffer, nullptr);
    if (buffer.memory) vkFreeMemory(device, buffer.memory, nullptr);
    buffer = {};
}

struct Accel {
    Buffer storage{};
    VkAccelerationStructureKHR handle = VK_NULL_HANDLE;
    VkDeviceAddress address = 0;
};

void destroyAccel(VkDevice device, PFN_vkDestroyAccelerationStructureKHR destroyAS, Accel& accel) {
    if (accel.handle) destroyAS(device, accel.handle, nullptr);
    destroyBuffer(device, accel.storage);
    accel = {};
}

void beginCommand(VkCommandBuffer cmd) {
    VkCommandBufferBeginInfo bi = vkStruct<VkCommandBufferBeginInfo>(VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    vkCheck(vkBeginCommandBuffer(cmd, &bi), "vkBeginCommandBuffer");
}

void submitAndWait(VkDevice device, VkQueue queue, VkCommandBuffer cmd) {
    VkFenceCreateInfo fi = vkStruct<VkFenceCreateInfo>(VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
    VkFence fence = VK_NULL_HANDLE;
    vkCheck(vkCreateFence(device, &fi, nullptr, &fence), "vkCreateFence");
    VkSubmitInfo si = vkStruct<VkSubmitInfo>(VK_STRUCTURE_TYPE_SUBMIT_INFO);
    si.commandBufferCount = 1;
    si.pCommandBuffers = &cmd;
    vkCheck(vkQueueSubmit(queue, 1, &si, fence), "vkQueueSubmit");
    vkCheck(vkWaitForFences(device, 1, &fence, VK_TRUE, std::numeric_limits<uint64_t>::max()), "vkWaitForFences");
    vkDestroyFence(device, fence, nullptr);
}

VkShaderModule makeShaderModule(VkDevice device, const std::vector<uint32_t>& words) {
    VkShaderModuleCreateInfo ci = vkStruct<VkShaderModuleCreateInfo>(VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO);
    ci.codeSize = words.size() * sizeof(uint32_t);
    ci.pCode = words.data();
    VkShaderModule out = VK_NULL_HANDLE;
    vkCheck(vkCreateShaderModule(device, &ci, nullptr, &out), "vkCreateShaderModule");
    return out;
}

void memoryBarrier(
    VkCommandBuffer cmd,
    VkPipelineStageFlags2 srcStage,
    VkAccessFlags2 srcAccess,
    VkPipelineStageFlags2 dstStage,
    VkAccessFlags2 dstAccess) {
    VkMemoryBarrier2 mb = vkStruct<VkMemoryBarrier2>(VK_STRUCTURE_TYPE_MEMORY_BARRIER_2);
    mb.srcStageMask = srcStage;
    mb.srcAccessMask = srcAccess;
    mb.dstStageMask = dstStage;
    mb.dstAccessMask = dstAccess;
    VkDependencyInfo di = vkStruct<VkDependencyInfo>(VK_STRUCTURE_TYPE_DEPENDENCY_INFO);
    di.memoryBarrierCount = 1;
    di.pMemoryBarriers = &mb;
    vkCmdPipelineBarrier2(cmd, &di);
}
} // namespace

int main(int argc, char** argv) {
    VkInstance instance = VK_NULL_HANDLE;
    VkDebugUtilsMessengerEXT messenger = VK_NULL_HANDLE;
    VkDevice device = VK_NULL_HANDLE;
    VkCommandPool commandPool = VK_NULL_HANDLE;
    std::array<VkCommandBuffer, 2> commands{VK_NULL_HANDLE, VK_NULL_HANDLE};
    VkPipeline pipeline = VK_NULL_HANDLE;
    std::array<VkShaderModule, 3> modules{VK_NULL_HANDLE, VK_NULL_HANDLE, VK_NULL_HANDLE};
    Buffer vertices{}, instances{}, blasScratch{}, tlasScratch{}, heap{}, output{}, sbt{};
    Accel blas{}, tlas{};

    try {
        const Args args = parseArgs(argc, argv);
        const auto raygenWords = readSpirv(args.raygen);
        const auto missWords = readSpirv(args.miss);
        const auto hitWords = readSpirv(args.closestHit);

        uint32_t loaderVersion = VK_API_VERSION_1_0;
        vkCheck(vkEnumerateInstanceVersion(&loaderVersion), "vkEnumerateInstanceVersion");
        if (loaderVersion < VK_API_VERSION_1_4)
            fail("Vulkan loader does not expose Vulkan 1.4");

        uint32_t layerCount = 0;
        vkCheck(vkEnumerateInstanceLayerProperties(&layerCount, nullptr), "vkEnumerateInstanceLayerProperties(count)");
        std::vector<VkLayerProperties> layers(layerCount);
        vkCheck(vkEnumerateInstanceLayerProperties(&layerCount, layers.data()), "vkEnumerateInstanceLayerProperties");
        if (!hasLayer(layers, "VK_LAYER_KHRONOS_validation"))
            fail("VK_LAYER_KHRONOS_validation is required");

        ValidationState validation{};
        VkDebugUtilsMessengerCreateInfoEXT debugInfo = vkStruct<VkDebugUtilsMessengerCreateInfoEXT>(VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT);
        debugInfo.messageSeverity = VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT | VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT;
        debugInfo.messageType = VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT |
            VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT | VK_DEBUG_UTILS_MESSAGE_TYPE_PERFORMANCE_BIT_EXT;
        debugInfo.pfnUserCallback = validationCallback;
        debugInfo.pUserData = &validation;

        VkApplicationInfo app = vkStruct<VkApplicationInfo>(VK_STRUCTURE_TYPE_APPLICATION_INFO);
        app.pApplicationName = "UFOAI M0.7 R4";
        app.apiVersion = VK_API_VERSION_1_4;
        const char* enabledLayer = "VK_LAYER_KHRONOS_validation";
        const char* instanceExt = VK_EXT_DEBUG_UTILS_EXTENSION_NAME;
        VkInstanceCreateInfo ici = vkStruct<VkInstanceCreateInfo>(VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO);
        ici.pNext = &debugInfo;
        ici.pApplicationInfo = &app;
        ici.enabledLayerCount = 1;
        ici.ppEnabledLayerNames = &enabledLayer;
        ici.enabledExtensionCount = 1;
        ici.ppEnabledExtensionNames = &instanceExt;
        vkCheck(vkCreateInstance(&ici, nullptr, &instance), "vkCreateInstance");

        auto createMessenger = reinterpret_cast<PFN_vkCreateDebugUtilsMessengerEXT>(vkGetInstanceProcAddr(instance, "vkCreateDebugUtilsMessengerEXT"));
        auto destroyMessenger = reinterpret_cast<PFN_vkDestroyDebugUtilsMessengerEXT>(vkGetInstanceProcAddr(instance, "vkDestroyDebugUtilsMessengerEXT"));
        if (!createMessenger || !destroyMessenger) fail("debug utils functions unavailable");
        vkCheck(createMessenger(instance, &debugInfo, nullptr, &messenger), "vkCreateDebugUtilsMessengerEXT");

        uint32_t physicalCount = 0;
        vkCheck(vkEnumeratePhysicalDevices(instance, &physicalCount, nullptr), "vkEnumeratePhysicalDevices(count)");
        std::vector<VkPhysicalDevice> physicals(physicalCount);
        vkCheck(vkEnumeratePhysicalDevices(instance, &physicalCount, physicals.data()), "vkEnumeratePhysicalDevices");
        VkPhysicalDevice physical = VK_NULL_HANDLE;
        VkPhysicalDeviceProperties props{};
        for (VkPhysicalDevice candidate : physicals) {
            VkPhysicalDeviceProperties p{};
            vkGetPhysicalDeviceProperties(candidate, &p);
            if (p.vendorID == kIntelVendorId && p.deviceID == kArcB580DeviceId) {
                physical = candidate;
                props = p;
                break;
            }
        }
        if (!physical) fail("exact Intel Arc B580 0x8086:0xe20b not found");
        if (props.apiVersion < VK_API_VERSION_1_4) fail("selected B580 device API is below Vulkan 1.4");

        uint32_t extCount = 0;
        vkCheck(vkEnumerateDeviceExtensionProperties(physical, nullptr, &extCount, nullptr), "device extensions(count)");
        std::vector<VkExtensionProperties> exts(extCount);
        vkCheck(vkEnumerateDeviceExtensionProperties(physical, nullptr, &extCount, exts.data()), "device extensions");
        const std::array<const char*, 6> requiredExts = {
            VK_EXT_DESCRIPTOR_HEAP_EXTENSION_NAME,
            VK_KHR_SHADER_UNTYPED_POINTERS_EXTENSION_NAME,
            VK_KHR_ACCELERATION_STRUCTURE_EXTENSION_NAME,
            VK_KHR_DEFERRED_HOST_OPERATIONS_EXTENSION_NAME,
            VK_KHR_RAY_TRACING_PIPELINE_EXTENSION_NAME,
            VK_KHR_RAY_TRACING_MAINTENANCE_1_EXTENSION_NAME,
        };
        for (const char* ext : requiredExts)
            if (!hasExtension(exts, ext)) fail(std::string("required B580 extension missing: ") + ext);

        VkPhysicalDeviceRayTracingMaintenance1FeaturesKHR maintenance = vkStruct<VkPhysicalDeviceRayTracingMaintenance1FeaturesKHR>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_RAY_TRACING_MAINTENANCE_1_FEATURES_KHR);
        VkPhysicalDeviceRayTracingPipelineFeaturesKHR rtFeatures = vkStruct<VkPhysicalDeviceRayTracingPipelineFeaturesKHR>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_RAY_TRACING_PIPELINE_FEATURES_KHR);
        VkPhysicalDeviceAccelerationStructureFeaturesKHR asFeatures = vkStruct<VkPhysicalDeviceAccelerationStructureFeaturesKHR>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ACCELERATION_STRUCTURE_FEATURES_KHR);
        VkPhysicalDeviceShaderUntypedPointersFeaturesKHR untyped = vkStruct<VkPhysicalDeviceShaderUntypedPointersFeaturesKHR>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_SHADER_UNTYPED_POINTERS_FEATURES_KHR);
        VkPhysicalDeviceDescriptorHeapFeaturesEXT heapFeatures = vkStruct<VkPhysicalDeviceDescriptorHeapFeaturesEXT>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DESCRIPTOR_HEAP_FEATURES_EXT);
        VkPhysicalDeviceVulkan13Features v13 = vkStruct<VkPhysicalDeviceVulkan13Features>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_3_FEATURES);
        VkPhysicalDeviceVulkan12Features v12 = vkStruct<VkPhysicalDeviceVulkan12Features>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES);
        VkPhysicalDeviceFeatures2 features = vkStruct<VkPhysicalDeviceFeatures2>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2);
        features.pNext = &v12;
        v12.pNext = &v13;
        v13.pNext = &heapFeatures;
        heapFeatures.pNext = &untyped;
        untyped.pNext = &asFeatures;
        asFeatures.pNext = &rtFeatures;
        rtFeatures.pNext = &maintenance;
        vkGetPhysicalDeviceFeatures2(physical, &features);
        if (!features.features.shaderInt64 || !v12.bufferDeviceAddress || !v12.scalarBlockLayout ||
            !v13.synchronization2 || !heapFeatures.descriptorHeap ||
            !untyped.shaderUntypedPointers || !asFeatures.accelerationStructure || !rtFeatures.rayTracingPipeline ||
            !rtFeatures.rayTracingPipelineTraceRaysIndirect || !rtFeatures.rayTraversalPrimitiveCulling ||
            !maintenance.rayTracingMaintenance1 || !maintenance.rayTracingPipelineTraceRaysIndirect2)
            fail("selected B580 is missing one or more mandatory R4 features");

        VkPhysicalDeviceRayTracingPipelinePropertiesKHR rtProps = vkStruct<VkPhysicalDeviceRayTracingPipelinePropertiesKHR>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_RAY_TRACING_PIPELINE_PROPERTIES_KHR);
        VkPhysicalDeviceAccelerationStructurePropertiesKHR asProps = vkStruct<VkPhysicalDeviceAccelerationStructurePropertiesKHR>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ACCELERATION_STRUCTURE_PROPERTIES_KHR);
        VkPhysicalDeviceDescriptorHeapPropertiesEXT heapProps = vkStruct<VkPhysicalDeviceDescriptorHeapPropertiesEXT>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DESCRIPTOR_HEAP_PROPERTIES_EXT);
        VkPhysicalDeviceProperties2 props2 = vkStruct<VkPhysicalDeviceProperties2>(VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2);
        props2.pNext = &heapProps;
        heapProps.pNext = &asProps;
        asProps.pNext = &rtProps;
        vkGetPhysicalDeviceProperties2(physical, &props2);
        const VkDeviceSize unifiedResourceStride = std::max(heapProps.imageDescriptorSize, heapProps.bufferDescriptorSize);
        if (heapProps.resourceHeapAlignment != 64 || heapProps.imageDescriptorSize != 64 ||
            heapProps.bufferDescriptorSize != 64 || heapProps.bufferDescriptorAlignment != 64 ||
            unifiedResourceStride != 64)
            fail("B580 descriptor-heap resource profile is not the accepted 64-byte unified layout");
        if (asProps.minAccelerationStructureScratchOffsetAlignment == 0)
            fail("invalid acceleration-structure scratch alignment");
        if (rtProps.maxRayRecursionDepth < 1) fail("ray recursion depth 1 unsupported");

        uint32_t qCount = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(physical, &qCount, nullptr);
        std::vector<VkQueueFamilyProperties> qProps(qCount);
        vkGetPhysicalDeviceQueueFamilyProperties(physical, &qCount, qProps.data());
        uint32_t queueFamily = UINT32_MAX;
        for (uint32_t i = 0; i < qCount; ++i) {
            if (qProps[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) { queueFamily = i; break; }
        }
        if (queueFamily == UINT32_MAX) fail("no graphics-capable B580 queue family");
        float priority = 1.0f;
        VkDeviceQueueCreateInfo qci = vkStruct<VkDeviceQueueCreateInfo>(VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO);
        qci.queueFamilyIndex = queueFamily;
        qci.queueCount = 1;
        qci.pQueuePriorities = &priority;

        features.features.shaderInt64 = VK_TRUE;
        v12.bufferDeviceAddress = VK_TRUE;
        v12.scalarBlockLayout = VK_TRUE;
        v13.synchronization2 = VK_TRUE;
        heapFeatures.descriptorHeap = VK_TRUE;
        heapFeatures.descriptorHeapCaptureReplay = VK_FALSE;
        untyped.shaderUntypedPointers = VK_TRUE;
        asFeatures.accelerationStructure = VK_TRUE;
        asFeatures.accelerationStructureCaptureReplay = VK_FALSE;
        asFeatures.accelerationStructureIndirectBuild = VK_FALSE;
        asFeatures.accelerationStructureHostCommands = VK_FALSE;
        asFeatures.descriptorBindingAccelerationStructureUpdateAfterBind = VK_FALSE;
        rtFeatures.rayTracingPipeline = VK_TRUE;
        rtFeatures.rayTracingPipelineShaderGroupHandleCaptureReplay = VK_FALSE;
        rtFeatures.rayTracingPipelineShaderGroupHandleCaptureReplayMixed = VK_FALSE;
        rtFeatures.rayTracingPipelineTraceRaysIndirect = VK_TRUE;
        rtFeatures.rayTraversalPrimitiveCulling = VK_TRUE;
        maintenance.rayTracingMaintenance1 = VK_TRUE;
        maintenance.rayTracingPipelineTraceRaysIndirect2 = VK_TRUE;

        VkDeviceCreateInfo dci = vkStruct<VkDeviceCreateInfo>(VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO);
        dci.pNext = &features;
        dci.queueCreateInfoCount = 1;
        dci.pQueueCreateInfos = &qci;
        dci.enabledExtensionCount = static_cast<uint32_t>(requiredExts.size());
        dci.ppEnabledExtensionNames = requiredExts.data();
        vkCheck(vkCreateDevice(physical, &dci, nullptr, &device), "vkCreateDevice");

        VkQueue queue = VK_NULL_HANDLE;
        vkGetDeviceQueue(device, queueFamily, 0, &queue);
        VkPhysicalDeviceMemoryProperties memoryProps{};
        vkGetPhysicalDeviceMemoryProperties(physical, &memoryProps);

        auto createAS = reinterpret_cast<PFN_vkCreateAccelerationStructureKHR>(vkGetDeviceProcAddr(device, "vkCreateAccelerationStructureKHR"));
        auto destroyAS = reinterpret_cast<PFN_vkDestroyAccelerationStructureKHR>(vkGetDeviceProcAddr(device, "vkDestroyAccelerationStructureKHR"));
        auto cmdBuildAS = reinterpret_cast<PFN_vkCmdBuildAccelerationStructuresKHR>(vkGetDeviceProcAddr(device, "vkCmdBuildAccelerationStructuresKHR"));
        auto getBuildSizes = reinterpret_cast<PFN_vkGetAccelerationStructureBuildSizesKHR>(vkGetDeviceProcAddr(device, "vkGetAccelerationStructureBuildSizesKHR"));
        auto getASAddress = reinterpret_cast<PFN_vkGetAccelerationStructureDeviceAddressKHR>(vkGetDeviceProcAddr(device, "vkGetAccelerationStructureDeviceAddressKHR"));
        auto createRTPipelines = reinterpret_cast<PFN_vkCreateRayTracingPipelinesKHR>(vkGetDeviceProcAddr(device, "vkCreateRayTracingPipelinesKHR"));
        auto getGroupHandles = reinterpret_cast<PFN_vkGetRayTracingShaderGroupHandlesKHR>(vkGetDeviceProcAddr(device, "vkGetRayTracingShaderGroupHandlesKHR"));
        auto cmdTraceRays = reinterpret_cast<PFN_vkCmdTraceRaysKHR>(vkGetDeviceProcAddr(device, "vkCmdTraceRaysKHR"));
        auto writeResources = reinterpret_cast<PFN_vkWriteResourceDescriptorsEXT>(vkGetDeviceProcAddr(device, "vkWriteResourceDescriptorsEXT"));
        auto bindResourceHeap = reinterpret_cast<PFN_vkCmdBindResourceHeapEXT>(vkGetDeviceProcAddr(device, "vkCmdBindResourceHeapEXT"));
        auto pushData = reinterpret_cast<PFN_vkCmdPushDataEXT>(vkGetDeviceProcAddr(device, "vkCmdPushDataEXT"));
        if (!createAS || !destroyAS || !cmdBuildAS || !getBuildSizes || !getASAddress || !createRTPipelines ||
            !getGroupHandles || !cmdTraceRays || !writeResources || !bindResourceHeap || !pushData)
            fail("one or more required Vulkan extension entry points are unavailable");

        VkCommandPoolCreateInfo cpci = vkStruct<VkCommandPoolCreateInfo>(VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
        cpci.queueFamilyIndex = queueFamily;
        cpci.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        vkCheck(vkCreateCommandPool(device, &cpci, nullptr, &commandPool), "vkCreateCommandPool");
        VkCommandBufferAllocateInfo cbai = vkStruct<VkCommandBufferAllocateInfo>(VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
        cbai.commandPool = commandPool;
        cbai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        cbai.commandBufferCount = static_cast<uint32_t>(commands.size());
        vkCheck(vkAllocateCommandBuffers(device, &cbai, commands.data()), "vkAllocateCommandBuffers");

        const std::array<float, 9> triangle = {-0.75f, -0.75f, 1.0f, 0.75f, -0.75f, 1.0f, 0.0f, 0.75f, 1.0f};
        vertices = createBuffer(device, memoryProps, sizeof(triangle),
            VK_BUFFER_USAGE_ACCELERATION_STRUCTURE_BUILD_INPUT_READ_ONLY_BIT_KHR | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, 0, true);
        std::memcpy(vertices.mapped, triangle.data(), sizeof(triangle));

        VkAccelerationStructureGeometryTrianglesDataKHR triangles = vkStruct<VkAccelerationStructureGeometryTrianglesDataKHR>(VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_GEOMETRY_TRIANGLES_DATA_KHR);
        triangles.vertexFormat = VK_FORMAT_R32G32B32_SFLOAT;
        triangles.vertexData.deviceAddress = vertices.address;
        triangles.vertexStride = 3 * sizeof(float);
        triangles.maxVertex = 2;
        triangles.indexType = VK_INDEX_TYPE_NONE_KHR;
        VkAccelerationStructureGeometryKHR blasGeometry = vkStruct<VkAccelerationStructureGeometryKHR>(VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_GEOMETRY_KHR);
        blasGeometry.geometryType = VK_GEOMETRY_TYPE_TRIANGLES_KHR;
        blasGeometry.geometry.triangles = triangles;
        blasGeometry.flags = VK_GEOMETRY_OPAQUE_BIT_KHR;
        VkAccelerationStructureBuildGeometryInfoKHR blasBuild = vkStruct<VkAccelerationStructureBuildGeometryInfoKHR>(VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_BUILD_GEOMETRY_INFO_KHR);
        blasBuild.type = VK_ACCELERATION_STRUCTURE_TYPE_BOTTOM_LEVEL_KHR;
        blasBuild.flags = VK_BUILD_ACCELERATION_STRUCTURE_PREFER_FAST_TRACE_BIT_KHR;
        blasBuild.mode = VK_BUILD_ACCELERATION_STRUCTURE_MODE_BUILD_KHR;
        blasBuild.geometryCount = 1;
        blasBuild.pGeometries = &blasGeometry;
        uint32_t primitiveCount = 1;
        VkAccelerationStructureBuildSizesInfoKHR blasSizes = vkStruct<VkAccelerationStructureBuildSizesInfoKHR>(VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_BUILD_SIZES_INFO_KHR);
        getBuildSizes(device, VK_ACCELERATION_STRUCTURE_BUILD_TYPE_DEVICE_KHR, &blasBuild, &primitiveCount, &blasSizes);
        blas.storage = createBuffer(device, memoryProps, blasSizes.accelerationStructureSize,
            VK_BUFFER_USAGE_ACCELERATION_STRUCTURE_STORAGE_BIT_KHR | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT,
            VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT, 0, true);
        VkAccelerationStructureCreateInfoKHR blasCreate = vkStruct<VkAccelerationStructureCreateInfoKHR>(VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_CREATE_INFO_KHR);
        blasCreate.buffer = blas.storage.buffer;
        blasCreate.size = blasSizes.accelerationStructureSize;
        blasCreate.type = VK_ACCELERATION_STRUCTURE_TYPE_BOTTOM_LEVEL_KHR;
        vkCheck(createAS(device, &blasCreate, nullptr, &blas.handle), "vkCreateAccelerationStructureKHR(BLAS)");
        VkAccelerationStructureDeviceAddressInfoKHR blasAddressInfo = vkStruct<VkAccelerationStructureDeviceAddressInfoKHR>(VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_DEVICE_ADDRESS_INFO_KHR);
        blasAddressInfo.accelerationStructure = blas.handle;
        blas.address = getASAddress(device, &blasAddressInfo);
        if (!blas.address) fail("BLAS address is zero");
        blasScratch = createBuffer(device, memoryProps,
            blasSizes.buildScratchSize + asProps.minAccelerationStructureScratchOffsetAlignment,
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT,
            VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT, 0, true);
        blasBuild.dstAccelerationStructure = blas.handle;
        blasBuild.scratchData.deviceAddress = alignUp(blasScratch.address, asProps.minAccelerationStructureScratchOffsetAlignment);

        VkAccelerationStructureInstanceKHR instanceData{};
        instanceData.transform.matrix[0][0] = 1.0f;
        instanceData.transform.matrix[1][1] = 1.0f;
        instanceData.transform.matrix[2][2] = 1.0f;
        instanceData.instanceCustomIndex = 0;
        instanceData.mask = 0xff;
        instanceData.instanceShaderBindingTableRecordOffset = 0;
        instanceData.flags = VK_GEOMETRY_INSTANCE_TRIANGLE_FACING_CULL_DISABLE_BIT_KHR;
        instanceData.accelerationStructureReference = blas.address;
        instances = createBuffer(device, memoryProps, sizeof(instanceData),
            VK_BUFFER_USAGE_ACCELERATION_STRUCTURE_BUILD_INPUT_READ_ONLY_BIT_KHR | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, 0, true);
        std::memcpy(instances.mapped, &instanceData, sizeof(instanceData));

        VkAccelerationStructureGeometryInstancesDataKHR instancesGeometryData = vkStruct<VkAccelerationStructureGeometryInstancesDataKHR>(VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_GEOMETRY_INSTANCES_DATA_KHR);
        instancesGeometryData.arrayOfPointers = VK_FALSE;
        instancesGeometryData.data.deviceAddress = instances.address;
        VkAccelerationStructureGeometryKHR tlasGeometry = vkStruct<VkAccelerationStructureGeometryKHR>(VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_GEOMETRY_KHR);
        tlasGeometry.geometryType = VK_GEOMETRY_TYPE_INSTANCES_KHR;
        tlasGeometry.geometry.instances = instancesGeometryData;
        VkAccelerationStructureBuildGeometryInfoKHR tlasBuild = vkStruct<VkAccelerationStructureBuildGeometryInfoKHR>(VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_BUILD_GEOMETRY_INFO_KHR);
        tlasBuild.type = VK_ACCELERATION_STRUCTURE_TYPE_TOP_LEVEL_KHR;
        tlasBuild.flags = VK_BUILD_ACCELERATION_STRUCTURE_PREFER_FAST_TRACE_BIT_KHR;
        tlasBuild.mode = VK_BUILD_ACCELERATION_STRUCTURE_MODE_BUILD_KHR;
        tlasBuild.geometryCount = 1;
        tlasBuild.pGeometries = &tlasGeometry;
        VkAccelerationStructureBuildSizesInfoKHR tlasSizes = vkStruct<VkAccelerationStructureBuildSizesInfoKHR>(VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_BUILD_SIZES_INFO_KHR);
        getBuildSizes(device, VK_ACCELERATION_STRUCTURE_BUILD_TYPE_DEVICE_KHR, &tlasBuild, &primitiveCount, &tlasSizes);
        tlas.storage = createBuffer(device, memoryProps, tlasSizes.accelerationStructureSize,
            VK_BUFFER_USAGE_ACCELERATION_STRUCTURE_STORAGE_BIT_KHR | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT,
            VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT, 0, true);
        VkAccelerationStructureCreateInfoKHR tlasCreate = vkStruct<VkAccelerationStructureCreateInfoKHR>(VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_CREATE_INFO_KHR);
        tlasCreate.buffer = tlas.storage.buffer;
        tlasCreate.size = tlasSizes.accelerationStructureSize;
        tlasCreate.type = VK_ACCELERATION_STRUCTURE_TYPE_TOP_LEVEL_KHR;
        vkCheck(createAS(device, &tlasCreate, nullptr, &tlas.handle), "vkCreateAccelerationStructureKHR(TLAS)");
        tlasScratch = createBuffer(device, memoryProps,
            tlasSizes.buildScratchSize + asProps.minAccelerationStructureScratchOffsetAlignment,
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT,
            VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT, 0, true);
        tlasBuild.dstAccelerationStructure = tlas.handle;
        tlasBuild.scratchData.deviceAddress = alignUp(tlasScratch.address, asProps.minAccelerationStructureScratchOffsetAlignment);

        VkAccelerationStructureBuildRangeInfoKHR range{};
        range.primitiveCount = 1;
        const VkAccelerationStructureBuildRangeInfoKHR* ranges[] = {&range};
        beginCommand(commands[0]);
        memoryBarrier(commands[0], VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_WRITE_BIT,
                      VK_PIPELINE_STAGE_2_ACCELERATION_STRUCTURE_BUILD_BIT_KHR,
                      VK_ACCESS_2_ACCELERATION_STRUCTURE_READ_BIT_KHR);
        cmdBuildAS(commands[0], 1, &blasBuild, ranges);
        memoryBarrier(commands[0], VK_PIPELINE_STAGE_2_ACCELERATION_STRUCTURE_BUILD_BIT_KHR,
                      VK_ACCESS_2_ACCELERATION_STRUCTURE_WRITE_BIT_KHR,
                      VK_PIPELINE_STAGE_2_ACCELERATION_STRUCTURE_BUILD_BIT_KHR,
                      VK_ACCESS_2_ACCELERATION_STRUCTURE_READ_BIT_KHR);
        cmdBuildAS(commands[0], 1, &tlasBuild, ranges);
        vkCheck(vkEndCommandBuffer(commands[0]), "vkEndCommandBuffer(build)");
        submitAndWait(device, queue, commands[0]);

        VkAccelerationStructureDeviceAddressInfoKHR tlasAddressInfo = vkStruct<VkAccelerationStructureDeviceAddressInfoKHR>(VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_DEVICE_ADDRESS_INFO_KHR);
        tlasAddressInfo.accelerationStructure = tlas.handle;
        tlas.address = getASAddress(device, &tlasAddressInfo);
        if (!tlas.address) fail("TLAS address is zero");

        output = createBuffer(device, memoryProps, 64,
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, 0, true);
        std::memset(output.mapped, 0, 64);

        const VkDeviceSize reservedBytes = heapProps.minResourceHeapReservedRange;
        const VkDeviceSize heapRangeBytes = kApplicationHeapBytes + reservedBytes;
        heap = createBuffer(device, memoryProps, heapRangeBytes + heapProps.resourceHeapAlignment,
            VK_BUFFER_USAGE_DESCRIPTOR_HEAP_BIT_EXT | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, 0, true);
        const VkDeviceAddress heapBase = alignUp(heap.address, heapProps.resourceHeapAlignment);
        const VkDeviceSize heapDelta = heapBase - heap.address;
        if (heapDelta + heapRangeBytes > heap.size) fail("aligned resource heap range exceeds backing buffer");
        auto* heapBytes = static_cast<uint8_t*>(heap.mapped) + heapDelta;

        if ((kAsByteOffset % 8) != 0 || (kOutputByteOffset % heapProps.bufferDescriptorAlignment) != 0)
            fail("R4 typed heap byte offsets violate their static alignment");
        if (!(kAsByteOffset + sizeof(uint64_t) <= kOutputByteOffset ||
              kOutputByteOffset + heapProps.bufferDescriptorSize <= kAsByteOffset))
            fail("AS and output descriptor byte allocations overlap");
        std::memcpy(heapBytes + kAsByteOffset, &tlas.address, sizeof(tlas.address));
        uint64_t publishedTlasAddress = 0;
        std::memcpy(&publishedTlasAddress, heapBytes + kAsByteOffset, sizeof(publishedTlasAddress));
        if (publishedTlasAddress != tlas.address)
            fail("published 8-byte TLAS heap value does not equal vkGetAccelerationStructureDeviceAddressKHR");

        VkDeviceAddressRangeEXT outputRange{};
        outputRange.address = output.address;
        outputRange.size = output.size;
        VkResourceDescriptorInfoEXT outputDescriptor = vkStruct<VkResourceDescriptorInfoEXT>(VK_STRUCTURE_TYPE_RESOURCE_DESCRIPTOR_INFO_EXT);
        outputDescriptor.type = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        outputDescriptor.data.pAddressRange = &outputRange;
        VkHostAddressRangeEXT descriptorDestination{};
        descriptorDestination.address = heapBytes + kOutputByteOffset;
        descriptorDestination.size = static_cast<size_t>(heapProps.bufferDescriptorSize);
        vkCheck(writeResources(device, 1, &outputDescriptor, &descriptorDestination), "vkWriteResourceDescriptorsEXT(output)");

        const uint64_t asTypedIndex = kAsByteOffset / 8;
        const uint64_t outputTypedIndex = kOutputByteOffset / unifiedResourceStride;

        modules[0] = makeShaderModule(device, raygenWords);
        modules[1] = makeShaderModule(device, missWords);
        modules[2] = makeShaderModule(device, hitWords);
        std::array<VkPipelineShaderStageCreateInfo, 3> stages{};
        const std::array<VkShaderStageFlagBits, 3> stageBits = {
            VK_SHADER_STAGE_RAYGEN_BIT_KHR, VK_SHADER_STAGE_MISS_BIT_KHR, VK_SHADER_STAGE_CLOSEST_HIT_BIT_KHR};
        for (size_t i = 0; i < stages.size(); ++i) {
            stages[i] = vkStruct<VkPipelineShaderStageCreateInfo>(VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO);
            stages[i].stage = stageBits[i];
            stages[i].module = modules[i];
            stages[i].pName = "main";
        }
        std::array<VkRayTracingShaderGroupCreateInfoKHR, 3> groups{};
        for (auto& group : groups) {
            group = vkStruct<VkRayTracingShaderGroupCreateInfoKHR>(VK_STRUCTURE_TYPE_RAY_TRACING_SHADER_GROUP_CREATE_INFO_KHR);
            group.generalShader = VK_SHADER_UNUSED_KHR;
            group.closestHitShader = VK_SHADER_UNUSED_KHR;
            group.anyHitShader = VK_SHADER_UNUSED_KHR;
            group.intersectionShader = VK_SHADER_UNUSED_KHR;
        }
        groups[0].type = VK_RAY_TRACING_SHADER_GROUP_TYPE_GENERAL_KHR;
        groups[0].generalShader = 0;
        groups[1].type = VK_RAY_TRACING_SHADER_GROUP_TYPE_GENERAL_KHR;
        groups[1].generalShader = 1;
        groups[2].type = VK_RAY_TRACING_SHADER_GROUP_TYPE_TRIANGLES_HIT_GROUP_KHR;
        groups[2].closestHitShader = 2;

        VkPipelineCreateFlags2CreateInfo flags2 = vkStruct<VkPipelineCreateFlags2CreateInfo>(VK_STRUCTURE_TYPE_PIPELINE_CREATE_FLAGS_2_CREATE_INFO);
        flags2.flags = VK_PIPELINE_CREATE_2_DESCRIPTOR_HEAP_BIT_EXT;
        VkRayTracingPipelineCreateInfoKHR rpci = vkStruct<VkRayTracingPipelineCreateInfoKHR>(VK_STRUCTURE_TYPE_RAY_TRACING_PIPELINE_CREATE_INFO_KHR);
        rpci.pNext = &flags2;
        rpci.stageCount = static_cast<uint32_t>(stages.size());
        rpci.pStages = stages.data();
        rpci.groupCount = static_cast<uint32_t>(groups.size());
        rpci.pGroups = groups.data();
        rpci.maxPipelineRayRecursionDepth = 1;
        rpci.layout = VK_NULL_HANDLE;
        vkCheck(createRTPipelines(device, VK_NULL_HANDLE, VK_NULL_HANDLE, 1, &rpci, nullptr, &pipeline), "vkCreateRayTracingPipelinesKHR");

        const VkDeviceSize handleSize = rtProps.shaderGroupHandleSize;
        const VkDeviceSize handleStride = alignUp(handleSize, rtProps.shaderGroupHandleAlignment);
        const VkDeviceSize regionSpacing = alignUp(handleStride, rtProps.shaderGroupBaseAlignment);
        if (handleStride > rtProps.maxShaderGroupStride) fail("SBT handle stride exceeds device maximum");
        std::vector<uint8_t> handles(static_cast<size_t>(3 * handleSize));
        vkCheck(getGroupHandles(device, pipeline, 0, 3, handles.size(), handles.data()), "vkGetRayTracingShaderGroupHandlesKHR");
        const VkDeviceSize sbtLogicalBytes = regionSpacing * 3;
        sbt = createBuffer(device, memoryProps, sbtLogicalBytes + rtProps.shaderGroupBaseAlignment,
            VK_BUFFER_USAGE_SHADER_BINDING_TABLE_BIT_KHR | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, 0, true);
        const VkDeviceAddress sbtBase = alignUp(sbt.address, rtProps.shaderGroupBaseAlignment);
        const VkDeviceSize sbtDelta = sbtBase - sbt.address;
        if (sbtDelta + sbtLogicalBytes > sbt.size) fail("aligned SBT range exceeds backing buffer");
        auto* sbtBytes = static_cast<uint8_t*>(sbt.mapped) + sbtDelta;
        std::memset(sbtBytes, 0, static_cast<size_t>(sbtLogicalBytes));
        for (size_t i = 0; i < 3; ++i)
            std::memcpy(sbtBytes + i * regionSpacing, handles.data() + i * handleSize, static_cast<size_t>(handleSize));
        VkStridedDeviceAddressRegionKHR raygenRegion{sbtBase + 0 * regionSpacing, handleStride, handleStride};
        VkStridedDeviceAddressRegionKHR missRegion{sbtBase + 1 * regionSpacing, handleStride, handleStride};
        VkStridedDeviceAddressRegionKHR hitRegion{sbtBase + 2 * regionSpacing, handleStride, handleStride};
        VkStridedDeviceAddressRegionKHR callableRegion{};

        beginCommand(commands[1]);
        memoryBarrier(commands[1],
                      VK_PIPELINE_STAGE_2_HOST_BIT | VK_PIPELINE_STAGE_2_ACCELERATION_STRUCTURE_BUILD_BIT_KHR,
                      VK_ACCESS_2_HOST_WRITE_BIT | VK_ACCESS_2_ACCELERATION_STRUCTURE_WRITE_BIT_KHR,
                      VK_PIPELINE_STAGE_2_RAY_TRACING_SHADER_BIT_KHR,
                      VK_ACCESS_2_ACCELERATION_STRUCTURE_READ_BIT_KHR |
                          VK_ACCESS_2_RESOURCE_HEAP_READ_BIT_EXT |
                          VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
        VkBindHeapInfoEXT heapBind = vkStruct<VkBindHeapInfoEXT>(VK_STRUCTURE_TYPE_BIND_HEAP_INFO_EXT);
        heapBind.heapRange.address = heapBase;
        heapBind.heapRange.size = heapRangeBytes;
        heapBind.reservedRangeOffset = kApplicationHeapBytes;
        heapBind.reservedRangeSize = reservedBytes;
        bindResourceHeap(commands[1], &heapBind);
        GpuShaderRoot root{};
        root.sceneRootAddress = asTypedIndex;
        root.passDataAddress = outputTypedIndex;
        VkPushDataInfoEXT push = vkStruct<VkPushDataInfoEXT>(VK_STRUCTURE_TYPE_PUSH_DATA_INFO_EXT);
        push.offset = 0;
        push.data.address = &root;
        push.data.size = sizeof(root);
        pushData(commands[1], &push);
        vkCmdBindPipeline(commands[1], VK_PIPELINE_BIND_POINT_RAY_TRACING_KHR, pipeline);
        cmdTraceRays(commands[1], &raygenRegion, &missRegion, &hitRegion, &callableRegion, 1, 1, 1);
        memoryBarrier(commands[1], VK_PIPELINE_STAGE_2_RAY_TRACING_SHADER_BIT_KHR,
                      VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                      VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_READ_BIT);
        vkCheck(vkEndCommandBuffer(commands[1]), "vkEndCommandBuffer(trace)");
        submitAndWait(device, queue, commands[1]);

        const auto* result = static_cast<const uint32_t*>(output.mapped);
        float hitT = 0.0f;
        std::memcpy(&hitT, &result[2], sizeof(hitT));
        if (result[0] != kHitMagic) {
            std::ostringstream out;
            out << "TraceRay known-triangle smoke returned 0x" << std::hex << result[0]
                << " instead of hit magic 0x" << kHitMagic;
            fail(out.str());
        }
        if (result[1] != static_cast<uint32_t>(asTypedIndex))
            fail("shader-observed AS typed index does not match pushed index");
        if (!std::isfinite(hitT) || std::fabs(hitT - 1.0f) > 0.01f)
            fail("known triangle hit distance is not finite and approximately 1.0");
        if (validation.warnings != 0 || validation.errors != 0)
            fail("Vulkan validation produced warnings/errors");

        std::cout << "device.name=" << props.deviceName << '\n';
        std::cout << "device.vendor_id=0x" << std::hex << props.vendorID << std::dec << '\n';
        std::cout << "device.device_id=0x" << std::hex << props.deviceID << std::dec << '\n';
        std::cout << "device.api=" << apiVersionString(props.apiVersion) << '\n';
        std::cout << "feature.shader_int64=true\n";
        std::cout << "feature.buffer_device_address=true\n";
        std::cout << "feature.scalar_block_layout=true\n";
        std::cout << "feature.synchronization2=true\n";
        std::cout << "feature.descriptor_heap=true\n";
        std::cout << "feature.shader_untyped_pointers=true\n";
        std::cout << "feature.acceleration_structure=true\n";
        std::cout << "feature.ray_tracing_pipeline=true\n";
        std::cout << "feature.ray_tracing_maintenance1=true\n";
        std::cout << "descriptor_heap.resource_alignment=" << heapProps.resourceHeapAlignment << '\n';
        std::cout << "descriptor_heap.buffer_descriptor_size=" << heapProps.bufferDescriptorSize << '\n';
        std::cout << "descriptor_heap.buffer_descriptor_alignment=" << heapProps.bufferDescriptorAlignment << '\n';
        std::cout << "descriptor_heap.unified_resource_stride=" << unifiedResourceStride << '\n';
        std::cout << "descriptor_heap.as_typed_stride=8\n";
        std::cout << "descriptor_heap.as_byte_offset=" << kAsByteOffset << '\n';
        std::cout << "descriptor_heap.as_typed_index=" << asTypedIndex << '\n';
        std::cout << "descriptor_heap.output_byte_offset=" << kOutputByteOffset << '\n';
        std::cout << "descriptor_heap.output_typed_index=" << outputTypedIndex << '\n';
        std::cout << "blas.device_address=" << hexAddress(blas.address) << '\n';
        std::cout << "tlas.device_address=" << hexAddress(tlas.address) << '\n';
        std::cout << "tlas.published_heap_value=" << hexAddress(publishedTlasAddress) << '\n';
        std::cout << "tlas.address_match=true\n";
        std::cout << "trace.hit_magic=0x" << std::hex << result[0] << std::dec << '\n';
        std::cout << "trace.hit_t=" << hitT << '\n';
        std::cout << "validation.warning_count=" << validation.warnings << '\n';
        std::cout << "validation.error_count=" << validation.errors << '\n';
        std::cout << "result=PASS\n";

        vkDeviceWaitIdle(device);
        if (pipeline) vkDestroyPipeline(device, pipeline, nullptr);
        for (auto module : modules) if (module) vkDestroyShaderModule(device, module, nullptr);
        destroyBuffer(device, sbt);
        destroyBuffer(device, output);
        destroyBuffer(device, heap);
        destroyBuffer(device, tlasScratch);
        destroyBuffer(device, blasScratch);
        destroyAccel(device, destroyAS, tlas);
        destroyAccel(device, destroyAS, blas);
        destroyBuffer(device, instances);
        destroyBuffer(device, vertices);
        if (commandPool) vkDestroyCommandPool(device, commandPool, nullptr);
        vkDestroyDevice(device, nullptr);
        device = VK_NULL_HANDLE;
        if (messenger) destroyMessenger(instance, messenger, nullptr);
        vkDestroyInstance(instance, nullptr);
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "M0.7 R4 native RT descriptor-heap fixture: FAIL: " << e.what() << '\n';
        if (device) vkDeviceWaitIdle(device);
        // Failure-path cleanup intentionally leaves extension-owned objects to device teardown.
        if (device) vkDestroyDevice(device, nullptr);
        if (instance) vkDestroyInstance(instance, nullptr);
        return 1;
    }
}
