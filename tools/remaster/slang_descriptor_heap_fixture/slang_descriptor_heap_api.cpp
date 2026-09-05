#include <slang-com-ptr.h>
#include <slang.h>

#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using Slang::ComPtr;

namespace
{
struct Args
{
    std::string source;
    std::string entry = "computeMain";
    std::string spv;
    std::string metadata;
};

Args parseArgs(int argc, char** argv)
{
    Args out;
    for (int i = 1; i < argc; ++i)
    {
        const std::string arg = argv[i];
        auto take = [&](std::string& dst)
        {
            if (++i >= argc)
                throw std::runtime_error("missing value after " + arg);
            dst = argv[i];
        };
        if (arg == "--source")
            take(out.source);
        else if (arg == "--entry")
            take(out.entry);
        else if (arg == "--spv")
            take(out.spv);
        else if (arg == "--metadata")
            take(out.metadata);
        else
            throw std::runtime_error("unknown argument: " + arg);
    }
    if (out.source.empty() || out.spv.empty() || out.metadata.empty())
        throw std::runtime_error("usage: --source FILE --entry NAME --spv FILE --metadata FILE");
    return out;
}

void printDiagnostics(slang::IBlob* diagnostics)
{
    if (diagnostics && diagnostics->getBufferSize())
        std::cerr << static_cast<const char*>(diagnostics->getBufferPointer());
}

void requireResult(SlangResult result, slang::IBlob* diagnostics, const char* what)
{
    printDiagnostics(diagnostics);
    if (SLANG_FAILED(result))
        throw std::runtime_error(std::string(what) + " failed");
}

slang::CompilerOptionEntry intOption(slang::CompilerOptionName name, int64_t value)
{
    slang::CompilerOptionEntry out = {};
    out.name = name;
    out.value.kind = slang::CompilerOptionValueKind::Int;
    out.value.intValue0 = value;
    return out;
}

slang::CompilerOptionEntry stringOption(slang::CompilerOptionName name, const char* value)
{
    slang::CompilerOptionEntry out = {};
    out.name = name;
    out.value.kind = slang::CompilerOptionValueKind::String;
    out.value.stringValue0 = value;
    return out;
}

void writeBlob(const std::string& path, slang::IBlob* blob)
{
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out)
        throw std::runtime_error("cannot open output: " + path);
    out.write(
        static_cast<const char*>(blob->getBufferPointer()),
        static_cast<std::streamsize>(blob->getBufferSize()));
    if (!out)
        throw std::runtime_error("failed writing output: " + path);
}

size_t fieldOffset(slang::TypeLayoutReflection* layout, int index)
{
    auto* field = layout->getFieldByIndex(index);
    if (!field)
        throw std::runtime_error("missing reflected struct field");
    return field->getOffset();
}

void writeMetadata(
    const std::string& path,
    const char* slangVersion,
    bool usesHeap,
    slang::ProgramLayout* layout)
{
    auto* rootType = layout->findTypeByName("GpuShaderRoot");
    auto* matrixType = layout->findTypeByName("MatrixAbiProbe");
    if (!rootType || !matrixType)
        throw std::runtime_error("required reflected fixture types are missing");

    auto* rootLayout = layout->getTypeLayout(rootType);
    auto* matrixLayout = layout->getTypeLayout(matrixType);
    if (!rootLayout || !matrixLayout)
        throw std::runtime_error("required reflected type layouts are missing");

    auto* matrixField = matrixLayout->getFieldByIndex(0);
    if (!matrixField || !matrixField->getTypeLayout())
        throw std::runtime_error("matrix reflection field is missing");

    const auto matrixMode = matrixField->getTypeLayout()->getMatrixLayoutMode();

    std::ofstream out(path, std::ios::trunc);
    if (!out)
        throw std::runtime_error("cannot open metadata output: " + path);
    out << "metadata.schema=1\n";
    out << "slang.version=" << (slangVersion ? slangVersion : "unknown") << "\n";
    out << "target.format=SPIRV\n";
    out << "target.profile=spirv_1_6\n";
    out << "target.vulkan=vulkan1.4\n";
    out << "target.capability.spvDescriptorHeapEXT=true\n";
    out << "target.capability.vk_mem_model=true\n";
    out << "target.fixture_profile_capabilities="
        << "SPV_GOOGLE_user_type,spvDerivativeControl,spvImageQuery,spvImageGatherExtended,"
        << "spvSparseResidency,spvMinLod,spvFragmentFullyCoveredEXT\n";
    out << "target.scalar_layout=true\n";
    out << "target.matrix_default=column-major\n";
    out << "target.resource_heap_stride=0\n";
    out << "target.sampler_heap_stride=0\n";
    out << "target.unified_resource_heap_stride=true\n";
    out << "target.optimization=maximal\n";
    out << "reflection.uses_bindless_resource_heap=" << (usesHeap ? "true" : "false") << "\n";
    out << "reflection.root.size=" << rootLayout->getSize() << "\n";
    out << "reflection.root.field_count=" << rootLayout->getFieldCount() << "\n";
    out << "reflection.root.offsets="
        << fieldOffset(rootLayout, 0) << ","
        << fieldOffset(rootLayout, 1) << ","
        << fieldOffset(rootLayout, 2) << ","
        << fieldOffset(rootLayout, 3) << "\n";
    out << "reflection.matrix_probe.size=" << matrixLayout->getSize() << "\n";
    out << "reflection.matrix_probe.offsets="
        << fieldOffset(matrixLayout, 0) << ","
        << fieldOffset(matrixLayout, 1) << ","
        << fieldOffset(matrixLayout, 2) << "\n";
    out << "reflection.matrix.layout="
        << (matrixMode == SLANG_MATRIX_LAYOUT_COLUMN_MAJOR ? "column-major" : "not-column-major")
        << "\n";
    if (!out)
        throw std::runtime_error("failed writing metadata: " + path);
}
} // namespace

int main(int argc, char** argv)
{
    try
    {
        const Args args = parseArgs(argc, argv);

        ComPtr<slang::IGlobalSession> global;
        requireResult(slang::createGlobalSession(global.writeRef()), nullptr, "createGlobalSession");

        std::vector<slang::CompilerOptionEntry> options;
        options.push_back(stringOption(slang::CompilerOptionName::Capability, "spvDescriptorHeapEXT"));
        options.push_back(stringOption(slang::CompilerOptionName::Capability, "vk_mem_model"));
        // Keep the explicit spirv_1_6 target closed over the capability requirements of this
        // qualification shader. Slang otherwise emits E41012 and silently upgrades the profile.
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

        slang::TargetDesc target = {};
        target.format = SLANG_SPIRV;
        target.profile = global->findProfile("spirv_1_6");
        target.forceGLSLScalarBufferLayout = true;
        target.compilerOptionEntries = options.data();
        target.compilerOptionEntryCount = static_cast<SlangInt>(options.size());

        slang::SessionDesc sessionDesc = {};
        sessionDesc.targets = &target;
        sessionDesc.targetCount = 1;
        sessionDesc.defaultMatrixLayoutMode = SLANG_MATRIX_LAYOUT_COLUMN_MAJOR;

        ComPtr<slang::ISession> session;
        requireResult(global->createSession(sessionDesc, session.writeRef()), nullptr, "createSession");

        ComPtr<slang::IBlob> diagnostics;
        ComPtr<slang::IModule> module;
        module = session->loadModule(args.source.c_str(), diagnostics.writeRef());
        printDiagnostics(diagnostics);
        if (!module)
            throw std::runtime_error("loadModule failed");

        ComPtr<slang::IEntryPoint> entry;
        diagnostics.setNull();
        requireResult(
            module->findEntryPointByName(args.entry.c_str(), entry.writeRef()),
            diagnostics,
            "findEntryPointByName");

        slang::IComponentType* components[] = {module.get(), entry.get()};
        ComPtr<slang::IComponentType> composite;
        diagnostics.setNull();
        requireResult(
            session->createCompositeComponentType(
                components, 2, composite.writeRef(), diagnostics.writeRef()),
            diagnostics,
            "createCompositeComponentType");

        ComPtr<slang::IComponentType> program;
        diagnostics.setNull();
        requireResult(composite->link(program.writeRef(), diagnostics.writeRef()), diagnostics, "link");

        ComPtr<slang::IBlob> spirv;
        diagnostics.setNull();
        requireResult(
            program->getEntryPointCode(0, 0, spirv.writeRef(), diagnostics.writeRef()),
            diagnostics,
            "getEntryPointCode");
        writeBlob(args.spv, spirv);

        ComPtr<slang::IMetadata> metadata;
        diagnostics.setNull();
        requireResult(
            program->getTargetMetadata(0, metadata.writeRef(), diagnostics.writeRef()),
            diagnostics,
            "getTargetMetadata");
        if (!metadata)
            throw std::runtime_error("Slang target metadata is null");
        auto* bindless = static_cast<slang::IBindlessResourceMetadata*>(
            metadata->castAs(slang::IBindlessResourceMetadata::getTypeGuid()));
        if (!bindless)
            throw std::runtime_error("IBindlessResourceMetadata is unavailable");
        const bool usesHeap = bindless->usesBindlessResourceHeap();
        if (!usesHeap)
            throw std::runtime_error("Slang target metadata says descriptor heap is unused");

        diagnostics.setNull();
        auto* layout = program->getLayout(0, diagnostics.writeRef());
        printDiagnostics(diagnostics);
        if (!layout)
            throw std::runtime_error("program reflection layout is null");
        writeMetadata(args.metadata, spGetBuildTagString(), usesHeap, layout);

        std::cout << "slang.api_linked=true\n";
        std::cout << "slang.version=" << spGetBuildTagString() << "\n";
        std::cout << "reflection.uses_bindless_resource_heap=true\n";
        std::cout << "result=PASS\n";
        return 0;
    }
    catch (const std::exception& e)
    {
        std::cerr << "M0.7 R3 Slang API fixture: FAIL: " << e.what() << "\n";
        return 1;
    }
}
