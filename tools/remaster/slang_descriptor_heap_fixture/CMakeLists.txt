cmake_minimum_required(VERSION 3.20)
project(ufoai_m0_slang_descriptor_heap_fixture LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(SLANG_ROOT "" CACHE PATH "Pinned Slang v2026.17 distribution root")
if(NOT SLANG_ROOT)
    message(FATAL_ERROR "SLANG_ROOT is required")
endif()

find_path(SLANG_INCLUDE_DIR
    NAMES slang.h slang-com-ptr.h
    PATHS "${SLANG_ROOT}/include"
    NO_DEFAULT_PATH)
if(NOT SLANG_INCLUDE_DIR)
    message(FATAL_ERROR "Pinned Slang headers not found under ${SLANG_ROOT}/include")
endif()

find_library(SLANG_COMPILER_LIBRARY
    NAMES slang-compiler slang
    PATHS "${SLANG_ROOT}/lib" "${SLANG_ROOT}/lib64" "${SLANG_ROOT}/bin"
    NO_DEFAULT_PATH)
if(NOT SLANG_COMPILER_LIBRARY)
    message(FATAL_ERROR "Pinned Slang compiler shared library not found under ${SLANG_ROOT}")
endif()

add_executable(m0_slang_descriptor_heap_api
    slang_descriptor_heap_api.cpp)
target_include_directories(m0_slang_descriptor_heap_api PRIVATE "${SLANG_INCLUDE_DIR}")
target_link_libraries(m0_slang_descriptor_heap_api PRIVATE "${SLANG_COMPILER_LIBRARY}")
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(m0_slang_descriptor_heap_api PRIVATE
        -Wall -Wextra -Wpedantic -Werror)
endif()

get_filename_component(SLANG_LIBRARY_DIR "${SLANG_COMPILER_LIBRARY}" DIRECTORY)
set_target_properties(m0_slang_descriptor_heap_api PROPERTIES
    BUILD_RPATH "${SLANG_LIBRARY_DIR}")

message(STATUS "M0.7 R3 Slang include: ${SLANG_INCLUDE_DIR}")
message(STATUS "M0.7 R3 Slang library: ${SLANG_COMPILER_LIBRARY}")
