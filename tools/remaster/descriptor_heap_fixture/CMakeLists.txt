cmake_minimum_required(VERSION 3.20)
project(ufoai_m0_descriptor_heap_fixture LANGUAGES CXX)

find_package(Vulkan 1.4 REQUIRED)

set(SLANGC "" CACHE FILEPATH "Pinned Slang v2026.17 compiler")
set(SPIRV_VAL "" CACHE FILEPATH "spirv-val executable")

if(NOT SLANGC OR NOT EXISTS "${SLANGC}")
    message(FATAL_ERROR "SLANGC must name the project-local Slang v2026.17 compiler")
endif()
if(NOT SPIRV_VAL OR NOT EXISTS "${SPIRV_VAL}")
    message(FATAL_ERROR "SPIRV_VAL must name spirv-val")
endif()

set(FIXTURE_SHADER_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/descriptor_heap_fixture.slang")
set(FIXTURE_SHADER_SPV "${CMAKE_CURRENT_BINARY_DIR}/descriptor_heap_fixture.spv")

add_custom_command(
    OUTPUT "${FIXTURE_SHADER_SPV}"
    COMMAND "${SLANGC}"
        "${FIXTURE_SHADER_SOURCE}"
        -target spirv
        -profile spirv_1_6
        -entry computeMain
        -stage compute
        -fvk-use-entrypoint-name
        -fvk-use-scalar-layout
        -o "${FIXTURE_SHADER_SPV}"
    COMMAND "${SPIRV_VAL}" --target-env vulkan1.4 "${FIXTURE_SHADER_SPV}"
    DEPENDS "${FIXTURE_SHADER_SOURCE}"
    VERBATIM
    COMMENT "Compiling and validating M0.7 descriptor-heap fixture shader"
)

add_custom_target(m0_descriptor_heap_shader ALL DEPENDS "${FIXTURE_SHADER_SPV}")

add_executable(m0_descriptor_heap_fixture descriptor_heap_fixture.cpp)
add_dependencies(m0_descriptor_heap_fixture m0_descriptor_heap_shader)
target_compile_features(m0_descriptor_heap_fixture PRIVATE cxx_std_20)
target_link_libraries(m0_descriptor_heap_fixture PRIVATE Vulkan::Vulkan)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(m0_descriptor_heap_fixture PRIVATE
        -Wall -Wextra -Wpedantic -Werror
    )
endif()
