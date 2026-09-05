# Copyright (C) 2026 UFO: Alien Invasion Remaster contributors.
# SPDX-License-Identifier: GPL-2.0-or-later

include_guard(GLOBAL)

set(_UFOAI_REMASTER_PRESENTATION_MODULE_DIR "${CMAKE_CURRENT_LIST_DIR}")

function(ufoai_remaster_configure_presentation_selection)
	set(_ufoai_presentation_components
		PLATFORM
		RENDERER
		UI
		AUDIO
		VFX
		CINEMATICS
	)
	set(_ufoai_selection_compile_definitions "")

	foreach(_ufoai_component IN LISTS _ufoai_presentation_components)
		set(_ufoai_selector "UFOAI_PRESENTATION_${_ufoai_component}")
		set(${_ufoai_selector} "LEGACY" CACHE STRING
			"Select the ${_ufoai_component} presentation implementation (LEGACY or REMASTER)")
		set_property(CACHE ${_ufoai_selector} PROPERTY STRINGS LEGACY REMASTER)

		string(TOUPPER "${${_ufoai_selector}}" _ufoai_selection)
		if (NOT _ufoai_selection STREQUAL "LEGACY" AND NOT _ufoai_selection STREQUAL "REMASTER")
			message(FATAL_ERROR
				"[remaster] Invalid ${_ufoai_selector}='${${_ufoai_selector}}'. "
				"Allowed values: LEGACY, REMASTER")
		endif()

		if (NOT "${${_ufoai_selector}}" STREQUAL "${_ufoai_selection}")
			set(${_ufoai_selector} "${_ufoai_selection}" CACHE STRING
				"Select the ${_ufoai_component} presentation implementation (LEGACY or REMASTER)" FORCE)
			set_property(CACHE ${_ufoai_selector} PROPERTY STRINGS LEGACY REMASTER)
		endif()

		if (_ufoai_selection STREQUAL "REMASTER")
			if (NOT UFOAI_REMASTER)
				message(FATAL_ERROR
					"[remaster] ${_ufoai_selector}=REMASTER requires UFOAI_REMASTER=ON. "
					"The legacy build cannot select an unwired remaster presentation path.")
			endif()
			message(FATAL_ERROR
				"[remaster] ${_ufoai_selector}=REMASTER is not implemented yet. "
				"M0.6 establishes the fail-closed selector/rollback contract only; "
				"the owning milestone must wire and validate this backend before it can be selected.")
		endif()

		set(UFOAI_PRESENTATION_${_ufoai_component}_IS_LEGACY 1)
		set(UFOAI_PRESENTATION_${_ufoai_component}_IS_REMASTER 0)
		list(APPEND _ufoai_selection_compile_definitions
			"UFOAI_PRESENTATION_${_ufoai_component}_LEGACY=1"
			"UFOAI_PRESENTATION_${_ufoai_component}_REMASTER=0"
		)
	endforeach()

	if (UFOAI_REMASTER)
		set(UFOAI_REMASTER_BOOTSTRAP_ENABLED 1)
	else()
		set(UFOAI_REMASTER_BOOTSTRAP_ENABLED 0)
	endif()

	set(_ufoai_generated_include_dir "${CMAKE_BINARY_DIR}/generated")
	set(_ufoai_generated_remaster_dir "${_ufoai_generated_include_dir}/ufoai/remaster")
	set(_ufoai_selection_manifest_dir "${CMAKE_BINARY_DIR}/remaster")
	file(MAKE_DIRECTORY "${_ufoai_generated_remaster_dir}" "${_ufoai_selection_manifest_dir}")

	configure_file(
		"${_UFOAI_REMASTER_PRESENTATION_MODULE_DIR}/PresentationSelection.h.in"
		"${_ufoai_generated_remaster_dir}/presentation_selection.h"
		@ONLY
	)
	configure_file(
		"${_UFOAI_REMASTER_PRESENTATION_MODULE_DIR}/presentation-selection.txt.in"
		"${_ufoai_selection_manifest_dir}/presentation-selection.txt"
		@ONLY
	)

	if (NOT TARGET ufoai_remaster_presentation_selection)
		add_library(ufoai_remaster_presentation_selection INTERFACE)
		target_include_directories(ufoai_remaster_presentation_selection
			INTERFACE "${_ufoai_generated_include_dir}")
		target_compile_definitions(ufoai_remaster_presentation_selection
			INTERFACE ${_ufoai_selection_compile_definitions})
	endif()

	if (NOT TARGET remaster-presentation-selection)
		add_custom_target(remaster-presentation-selection
			COMMAND "${CMAKE_COMMAND}" -E cat
				"${_ufoai_selection_manifest_dir}/presentation-selection.txt"
			VERBATIM
		)
	endif()

	message(STATUS
		"[remaster] Presentation selection: "
		"platform=${UFOAI_PRESENTATION_PLATFORM}, "
		"renderer=${UFOAI_PRESENTATION_RENDERER}, "
		"ui=${UFOAI_PRESENTATION_UI}, "
		"audio=${UFOAI_PRESENTATION_AUDIO}, "
		"vfx=${UFOAI_PRESENTATION_VFX}, "
		"cinematics=${UFOAI_PRESENTATION_CINEMATICS}")
	message(STATUS "[remaster] M0.6 selection scaffold retains legacy production behavior")
endfunction()
