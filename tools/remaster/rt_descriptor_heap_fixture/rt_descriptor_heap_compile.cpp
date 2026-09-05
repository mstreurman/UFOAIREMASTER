#include <slang-com-ptr.h>
#include <slang.h>

#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using Slang::ComPtr;

namespace {
struct Args {
    std::string source;
    std::string outDir;
    std::string metadata;
};

Args parseArgs(int argc, char** argv) {
    Args out;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        auto take = [&](std::string& dst) {
            if (++i >= argc)
                throw std::runtime_error("missing value after " + arg);
            dst = argv[i];
        };
        if (arg == "--source") take(out.source);
        else if (arg == "--out-dir") take(out.outDir);
        else if (arg == "--metadata") take(out.metadata);
        else throw std::runtime_error("unknown argument: " + arg);
    }
    if (out.source.empty() || out.outDir.empty() || out.metadata.empty())
        throw std::runtime_error("usage: --source FILE --out-dir DIR --metadata FILE");
    return out;
}

std::string diagnosticsText(slang::IBlob* diagnostics) {
    if (!diagnostics || diagnostics->getBufferSize() == 0)
        return {};
    return std::string(
        static_cast<const char*>(diagnostics->getBufferPointer()),
        diagnostics->getBufferSize());
}

void requireClean(SlangResult result, slang::IBlob* diagnostics, const char* what) {
    const std::string text = diagnosticsText(diagnostics);
    if (!text.empty()) {
        std::cerr << text;
        throw std::runtime_error(std::string(what) + " emitted diagnostics; R4 requires clean diagnostics");
    }
    if (SLANG_FAILED(result))
        throw std::runtime_error(std::string(what) + " failed");
}

slang::CompilerOptionEntry intOption(slang::CompilerOptionName name, int64_t value) {
    slang::CompilerOptionEntry out{};
    out.name = name;
    out.value.kind = slang::CompilerOptionValueKind::Int;
    out.value.intValue0 = value;
    return out;
}

slang::CompilerOptionEntry stringOption(slang::CompilerOptionName name, const char* value) {
    slang::CompilerOptionEntry out{};
    out.name = name;
    out.value.kind = slang::CompilerOptionValueKind::String;
    out.value.stringValue0 = value;
    return out;
}

void writeBlob(const std::string& path, slang::IBlob* blob) {
    if (!blob || blob->getBufferSize() == 0)
        throw std::runtime_error("empty SPIR-V blob for " + path);
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out)
        throw std::runtime_error("cannot open output: " + path);
    out.write(static_cast<const char*>(blob->getBufferPointer()),
              static_cast<std::streamsize>(blob->getBufferSize()));
    if (!out)
        throw std::runtime_error("failed writing output: " + path);
}

size_t fieldOffset(slang::TypeLayoutReflection* layout, int index) {
    auto* field = layout->getFieldByIndex(index);
    if (!field)
        throw std::runtime_error("missing GpuShaderRoot reflected field");
    return field->getOffset();
}
} // namespace

int main(int argc, char** argv) {
    try {
        const Args args = parseArgs(argc, argv);
        const std::array<const char*, 3> entryNames = {"rayGenMain", "missMain", "closestHitMain"};
        const std::array<const char*, 3> outputNames = {"raygen.spv", "miss.spv", "closesthit.spv"};

        ComPtr<slang::IGlobalSession> global;
        if (SLANG_FAILED(slang::createGlobalSession(global.writeRef())))
            throw std::runtime_error("createGlobalSession failed");

        std::vector<slang::CompilerOptionEntry> options;
        options.push_back(stringOption(slang::CompilerOptionName::Capability, "spvDescriptorHeapEXT"));
        options.push_back(stringOption(slang::CompilerOptionName::Capability, "spvRayTracingKHR"));
        options.push_back(stringOption(slang::CompilerOptionName::Capability, "vk_mem_model"));
        // Same explicit SPIR-V profile closure accepted by R3, plus ray tracing above.
        options.push_back(stringOption(slang::CompilerOptionName::Capability, "SPV_GOOGLE_user_type"));
        options.push_back(stringOption(slang::CompilerOptionName::Capability, "spvDerivativeControl"));
        options.push_back(stringOption(slang::CompilerOptionName::Capability, "spvImageQuery"));
        options.push_back(stringOption(slang::CompilerOptionName::Capability, "spvImageGatherExtended"));
        options.push_back(stringOption(slang::CompilerOptionName::Capability, "spvSparseResidency"));
        options.push_back(stringOption(slang::CompilerOptionName::Capability, "spvMinLod"));
        options.push_back(stringOption(slang::CompilerOptionName::Capability, "spvFragmentFullyCoveredEXT"));
        options.push_back(intOption(slang::CompilerOptionName::SPIRVResourceHeapStride, 0));
        options.push_back(intOption(slang::CompilerOptionName::SPIRVSamplerHeapStride, 0));
        options.push_back(intOption(slang::CompilerOptionName::SPIRVUnifiedDescriptorHeapStride, 1));
        options.push_back(intOption(
            slang::CompilerOptionName::Optimization,
            static_cast<int64_t>(SLANG_OPTIMIZATION_LEVEL_MAXIMAL)));

        slang::TargetDesc target{};
        target.format = SLANG_SPIRV;
        target.profile = global->findProfile("spirv_1_6");
        target.forceGLSLScalarBufferLayout = true;
        target.compilerOptionEntries = options.data();
        target.compilerOptionEntryCount = static_cast<SlangInt>(options.size());

        slang::SessionDesc sessionDesc{};
        sessionDesc.targets = &target;
        sessionDesc.targetCount = 1;
        sessionDesc.defaultMatrixLayoutMode = SLANG_MATRIX_LAYOUT_COLUMN_MAJOR;

        ComPtr<slang::ISession> session;
        if (SLANG_FAILED(global->createSession(sessionDesc, session.writeRef())))
            throw std::runtime_error("createSession failed");

        ComPtr<slang::IBlob> diagnostics;
        ComPtr<slang::IModule> module;
        module = session->loadModule(args.source.c_str(), diagnostics.writeRef());
        if (!diagnosticsText(diagnostics).empty()) {
            std::cerr << diagnosticsText(diagnostics);
            throw std::runtime_error("loadModule emitted diagnostics; R4 requires clean diagnostics");
        }
        if (!module)
            throw std::runtime_error("loadModule failed");

        std::array<ComPtr<slang::IEntryPoint>, 3> entries;
        for (size_t i = 0; i < entries.size(); ++i) {
            diagnostics.setNull();
            const SlangResult result = module->findEntryPointByName(entryNames[i], entries[i].writeRef());
            requireClean(result, diagnostics, "findEntryPointByName");
        }

        std::array<slang::IComponentType*, 4> components = {
            module.get(), entries[0].get(), entries[1].get(), entries[2].get()};
        ComPtr<slang::IComponentType> composite;
        diagnostics.setNull();
        requireClean(
            session->createCompositeComponentType(
                components.data(), static_cast<SlangInt>(components.size()),
                composite.writeRef(), diagnostics.writeRef()),
            diagnostics, "createCompositeComponentType");

        ComPtr<slang::IComponentType> program;
        diagnostics.setNull();
        requireClean(composite->link(program.writeRef(), diagnostics.writeRef()), diagnostics, "link");

        for (size_t i = 0; i < entries.size(); ++i) {
            ComPtr<slang::IBlob> spirv;
            diagnostics.setNull();
            requireClean(
                program->getEntryPointCode(static_cast<SlangInt>(i), 0, spirv.writeRef(), diagnostics.writeRef()),
                diagnostics, "getEntryPointCode");
            writeBlob(args.outDir + "/" + outputNames[i], spirv);
        }

        ComPtr<slang::IMetadata> metadata;
        diagnostics.setNull();
        requireClean(program->getTargetMetadata(0, metadata.writeRef(), diagnostics.writeRef()),
                     diagnostics, "getTargetMetadata");
        if (!metadata)
            throw std::runtime_error("target metadata is null");
        auto* bindless = static_cast<slang::IBindlessResourceMetadata*>(
            metadata->castAs(slang::IBindlessResourceMetadata::getTypeGuid()));
        if (!bindless || !bindless->usesBindlessResourceHeap())
            throw std::runtime_error("target metadata does not confirm descriptor-heap use");

        diagnostics.setNull();
        auto* layout = program->getLayout(0, diagnostics.writeRef());
        if (!diagnosticsText(diagnostics).empty()) {
            std::cerr << diagnosticsText(diagnostics);
            throw std::runtime_error("getLayout emitted diagnostics");
        }
        if (!layout)
            throw std::runtime_error("program layout is null");
        auto* rootType = layout->findTypeByName("GpuShaderRoot");
        if (!rootType)
            throw std::runtime_error("GpuShaderRoot reflection type missing");
        auto* rootLayout = layout->getTypeLayout(rootType);
        if (!rootLayout || rootLayout->getFieldCount() != 4 || rootLayout->getSize() != 32)
            throw std::runtime_error("GpuShaderRoot reflection does not match v1 32-byte root");

        std::ofstream meta(args.metadata, std::ios::trunc);
        if (!meta)
            throw std::runtime_error("cannot open metadata output");
        meta << "metadata.schema=1\n";
        meta << "slang.version=" << spGetBuildTagString() << "\n";
        meta << "target.profile=spirv_1_6\n";
        meta << "target.vulkan=vulkan1.4\n";
        meta << "target.capability.spvDescriptorHeapEXT=true\n";
        meta << "target.capability.spvRayTracingKHR=true\n";
        meta << "target.vulkan_memory_model=true\n";
        meta << "target.resource_heap_stride=0\n";
        meta << "target.unified_resource_heap_stride=true\n";
        meta << "target.matrix_default=column-major\n";
        meta << "reflection.uses_bindless_resource_heap=true\n";
        meta << "reflection.root.size=" << rootLayout->getSize() << "\n";
        meta << "reflection.root.offsets="
             << fieldOffset(rootLayout, 0) << ',' << fieldOffset(rootLayout, 1) << ','
             << fieldOffset(rootLayout, 2) << ',' << fieldOffset(rootLayout, 3) << "\n";
        if (!meta)
            throw std::runtime_error("failed writing metadata");

        std::cout << "slang.api_linked=true\n";
        std::cout << "slang.version=" << spGetBuildTagString() << "\n";
        std::cout << "reflection.uses_bindless_resource_heap=true\n";
        std::cout << "result=PASS\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "M0.7 R4 Slang compiler fixture: FAIL: " << e.what() << '\n';
        return 1;
    }
}
