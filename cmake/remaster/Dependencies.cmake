# Copyright (C) 2026 UFO: Alien Invasion Remaster contributors.
# SPDX-License-Identifier: GPL-2.0-or-later

include_guard(GLOBAL)

function(ufoai_remaster_probe_dependencies)
	message(STATUS "[remaster] M0 dependency discovery enabled")
	message(STATUS "[remaster] Legacy SDL2/OpenGL targets remain unchanged")

	set(_ufoai_missing_dependencies "")

	# Vulkan headers/loader. Runtime extension qualification is a later native fixture.
	find_package(Vulkan 1.4 QUIET)
	if (Vulkan_FOUND)
		if (DEFINED Vulkan_VERSION)
			message(STATUS "[remaster] Vulkan: ${Vulkan_VERSION}")
		else()
			message(STATUS "[remaster] Vulkan: found (>= 1.4)")
		endif()
	else()
		list(APPEND _ufoai_missing_dependencies "Vulkan >= 1.4 development package")
	endif()

	# Fedora platform/runtime development dependencies. PkgConfig supplies the
	# version checks that legacy Find modules do not consistently expose.
	find_package(PkgConfig QUIET)
	if (NOT PkgConfig_FOUND)
		list(APPEND _ufoai_missing_dependencies "pkg-config")
	else()
		pkg_check_modules(UFOAI_SDL3 QUIET IMPORTED_TARGET sdl3>=3.4)
		if (UFOAI_SDL3_FOUND)
			message(STATUS "[remaster] SDL3: ${UFOAI_SDL3_VERSION}")
		else()
			list(APPEND _ufoai_missing_dependencies "SDL3 >= 3.4")
		endif()

		pkg_check_modules(UFOAI_OPENAL QUIET IMPORTED_TARGET openal>=1.24)
		if (UFOAI_OPENAL_FOUND)
			message(STATUS "[remaster] OpenAL: ${UFOAI_OPENAL_VERSION}")
		else()
			list(APPEND _ufoai_missing_dependencies "OpenAL >= 1.24")
		endif()

		pkg_check_modules(
			UFOAI_FFMPEG
			QUIET
			IMPORTED_TARGET
			libavcodec>=62
			libavformat>=62
			libavutil>=60
			libswresample>=6
			libswscale>=9
		)
		if (UFOAI_FFMPEG_FOUND)
			message(STATUS "[remaster] FFmpeg development modules: accepted API majors found")
		else()
			list(APPEND _ufoai_missing_dependencies "FFmpeg 8.x development modules (libavcodec 62/libavformat 62/libavutil 60/libswresample 6/libswscale 9)")
		endif()
	endif()

	# Slang is a project-local build-time tool, intentionally not a committed binary.
	if (NOT UFOAI_SLANGC_EXECUTABLE)
		find_program(
			UFOAI_SLANGC_EXECUTABLE
			NAMES slangc
			HINTS "${UFOAI_REMASTER_SLANG_ROOT}/bin"
			NO_DEFAULT_PATH
		)
	endif()

	if (UFOAI_SLANGC_EXECUTABLE)
		execute_process(
			COMMAND "${UFOAI_SLANGC_EXECUTABLE}" -version
			RESULT_VARIABLE _ufoai_slang_result
			OUTPUT_VARIABLE _ufoai_slang_stdout
			ERROR_VARIABLE _ufoai_slang_stderr
			OUTPUT_STRIP_TRAILING_WHITESPACE
			ERROR_STRIP_TRAILING_WHITESPACE
		)
		set(_ufoai_slang_output "${_ufoai_slang_stdout}\n${_ufoai_slang_stderr}")
		string(REGEX MATCH "[0-9][0-9][0-9][0-9]\\.[0-9][0-9]*" _ufoai_slang_version "${_ufoai_slang_output}")
		if (_ufoai_slang_result EQUAL 0 AND _ufoai_slang_version STREQUAL "2026.17")
			message(STATUS "[remaster] Slang: ${_ufoai_slang_version} (${UFOAI_SLANGC_EXECUTABLE})")
		else()
			list(APPEND _ufoai_missing_dependencies "project-local Slang exactly 2026.17")
		endif()
	else()
		list(APPEND _ufoai_missing_dependencies "project-local Slang exactly 2026.17")
	endif()

	# Jolt is vendored source. M0.2 verifies the accepted identity markers; M0.3
	# will recompute the complete sorted-file BLAKE3 identity from the clean tree.
	set(_ufoai_jolt_manifest "${UFOAI_REMASTER_JOLT_ROOT}/UFOAI_VENDOR_MANIFEST.txt")
	set(_ufoai_jolt_core "${UFOAI_REMASTER_JOLT_ROOT}/Jolt/Core/Core.h")
	set(_ufoai_jolt_ok TRUE)

	if (NOT EXISTS "${_ufoai_jolt_manifest}" OR NOT EXISTS "${_ufoai_jolt_core}")
		set(_ufoai_jolt_ok FALSE)
	else()
		file(READ "${_ufoai_jolt_manifest}" _ufoai_jolt_manifest_text)
		foreach(_ufoai_jolt_marker IN ITEMS
			"release_tag=v5.6.0"
			"commit_sha=e77f175595e64cb44218cc9d9d56fc365ad0e36a"
			"license_identifier=MIT"
			"sorted_file_manifest_blake3_256=ffe175b315e20631eea26419b65ef225b73e37e3788dd93b66407fb3f37a9df2"
			"local_patch_list=none"
		)
			string(FIND "${_ufoai_jolt_manifest_text}" "${_ufoai_jolt_marker}" _ufoai_jolt_marker_pos)
			if (_ufoai_jolt_marker_pos EQUAL -1)
				set(_ufoai_jolt_ok FALSE)
			endif()
		endforeach()

		file(READ "${_ufoai_jolt_core}" _ufoai_jolt_core_text)
		foreach(_ufoai_jolt_version_marker IN ITEMS
			"#define JPH_VERSION_MAJOR 5"
			"#define JPH_VERSION_MINOR 6"
			"#define JPH_VERSION_PATCH 0"
		)
			string(FIND "${_ufoai_jolt_core_text}" "${_ufoai_jolt_version_marker}" _ufoai_jolt_version_pos)
			if (_ufoai_jolt_version_pos EQUAL -1)
				set(_ufoai_jolt_ok FALSE)
			endif()
		endforeach()
	endif()

	if (_ufoai_jolt_ok)
		message(STATUS "[remaster] Jolt: v5.6.0 accepted vendor identity markers found")
	else()
		list(APPEND _ufoai_missing_dependencies "vendored Jolt v5.6.0 accepted identity")
	endif()

	find_program(UFOAI_SPIRV_VAL_EXECUTABLE NAMES spirv-val)
	if (UFOAI_SPIRV_VAL_EXECUTABLE)
		message(STATUS "[remaster] spirv-val: ${UFOAI_SPIRV_VAL_EXECUTABLE}")
	else()
		list(APPEND _ufoai_missing_dependencies "spirv-val")
	endif()

	find_program(UFOAI_B3SUM_EXECUTABLE NAMES b3sum)
	if (UFOAI_B3SUM_EXECUTABLE)
		message(STATUS "[remaster] b3sum: ${UFOAI_B3SUM_EXECUTABLE}")
	else()
		list(APPEND _ufoai_missing_dependencies "b3sum")
	endif()

	find_program(UFOAI_CCACHE_EXECUTABLE NAMES ccache)
	if (UFOAI_CCACHE_EXECUTABLE)
		message(STATUS "[remaster] ccache: ${UFOAI_CCACHE_EXECUTABLE}")
	else()
		list(APPEND _ufoai_missing_dependencies "ccache")
	endif()

	if (_ufoai_missing_dependencies)
		list(JOIN _ufoai_missing_dependencies ", " _ufoai_missing_text)
		if (UFOAI_REMASTER_STRICT_DEPENDENCIES)
			message(FATAL_ERROR "[remaster] Missing/incorrect M0 dependencies: ${_ufoai_missing_text}")
		else()
			message(WARNING "[remaster] Missing/incorrect M0 dependencies: ${_ufoai_missing_text}")
		endif()
	else()
		message(STATUS "[remaster] M0 dependency discovery: PASS")
	endif()
endfunction()
