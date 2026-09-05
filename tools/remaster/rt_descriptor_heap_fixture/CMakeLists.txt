cmake_minimum_required(VERSION 3.25)
project(ufoai_m0_rt_descriptor_heap_fixture LANGUAGES CXX)

if(NOT DEFINED SLANG_ROOT)
    message(FATAL_ERROR "SLANG_ROOT must point at the pinned Slang v2026.17 distribution")
endif()

find_package(Vulkan REQUIRED)

set(SLANG_INCLUDE_DIR "${SLANG_ROOT}/include")
find_library(SLANG_COMPILER_LIBRARY
    NAMES slang-compiler slang
    PATHS "${SLANG_ROOT}/lib" "${SLANG_ROOT}/bin"
    NO_DEFAULT_PATH)

if(NOT EXISTS "${SLANG_INCLUDE_DIR}/slang.h")
    message(FATAL_ERROR "Missing ${SLANG_INCLUDE_DIR}/slang.h")
endif()
if(NOT SLANG_COMPILER_LIBRARY)
    message(FATAL_ERROR "Pinned Slang compiler shared library not found under ${SLANG_ROOT}")
endif()

add_executable(m0_rt_descriptor_heap_compile rt_descriptor_heap_compile.cpp)
target_compile_features(m0_rt_descriptor_heap_compile PRIVATE cxx_std_20)
target_include_directories(m0_rt_descriptor_heap_compile PRIVATE "${SLANG_INCLUDE_DIR}")
target_link_libraries(m0_rt_descriptor_heap_compile PRIVATE "${SLANG_COMPILER_LIBRARY}")
target_compile_options(m0_rt_descriptor_heap_compile PRIVATE -Wall -Wextra -Wpedantic -Werror)
set_target_properties(m0_rt_descriptor_heap_compile PROPERTIES BUILD_RPATH "${SLANG_ROOT}/lib;${SLANG_ROOT}/bin")

add_executable(m0_rt_descriptor_heap_native rt_descriptor_heap_native.cpp)
target_compile_features(m0_rt_descriptor_heap_native PRIVATE cxx_std_20)
target_link_libraries(m0_rt_descriptor_heap_native PRIVATE Vulkan::Vulkan)
target_compile_options(m0_rt_descriptor_heap_native PRIVATE -Wall -Wextra -Wpedantic -Werror)

message(STATUS "M0.7 R4 Slang include: ${SLANG_INCLUDE_DIR}")
message(STATUS "M0.7 R4 Slang library: ${SLANG_COMPILER_LIBRARY}")
