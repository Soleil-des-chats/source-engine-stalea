"""Patch SDL2 for iOS cross-compilation issues.

Run from the repository root. Idempotent: safe to run even if already patched.

1. thirdparty/SDL-src/CMakeLists.txt unconditionally promotes
   -Wdeclaration-after-statement to a hard error (-Werror=...) whenever the
   compiler supports it, which AppleClang does. This old codebase has many
   spots (across several .m files) that violate that rule in ways that are
   harmless in practice, so rather than patching every offending file one at
   a time as they surface, we downgrade this one flag back to a warning.
2. SDL_rwopsbundlesupport.m has one specific declaration-after-statement
   violation that's easy to fix at the source, so it's fixed directly too
   (keeps the diff small even with the flag downgraded).
"""

# --- 1. Stop -Wdeclaration-after-statement from being promoted to -Werror ---

cmake_path = "thirdparty/SDL-src/CMakeLists.txt"

cmake_old = """  check_c_compiler_flag(-Wdeclaration-after-statement HAVE_GCC_WDECLARATION_AFTER_STATEMENT)
  if(HAVE_GCC_WDECLARATION_AFTER_STATEMENT)
    check_c_compiler_flag(-Werror=declaration-after-statement HAVE_GCC_WERROR_DECLARATION_AFTER_STATEMENT)
    if(HAVE_GCC_WERROR_DECLARATION_AFTER_STATEMENT)
      list(APPEND EXTRA_CFLAGS "-Werror=declaration-after-statement")
    endif()
    list(APPEND EXTRA_CFLAGS "-Wdeclaration-after-statement")
  endif()"""

cmake_new = """  check_c_compiler_flag(-Wdeclaration-after-statement HAVE_GCC_WDECLARATION_AFTER_STATEMENT)
  if(HAVE_GCC_WDECLARATION_AFTER_STATEMENT)
    list(APPEND EXTRA_CFLAGS "-Wdeclaration-after-statement")
  endif()"""

with open(cmake_path) as f:
    cmake_content = f.read()

if cmake_new in cmake_content:
    print("CMakeLists.txt already patched, nothing to do.")
elif cmake_old in cmake_content:
    cmake_content = cmake_content.replace(cmake_old, cmake_new, 1)
    with open(cmake_path, "w") as f:
        f.write(cmake_content)
    print("CMakeLists.txt patched successfully.")
else:
    raise SystemExit(
        "ERROR: expected text not found in " + cmake_path +
        " - upstream SDL2 source may have changed, patch needs updating."
    )

# --- 2. Fix the one easy declaration-after-statement violation at its source ---

path = "thirdparty/SDL-src/src/file/cocoa/SDL_rwopsbundlesupport.m"

old = """    FILE* fp = NULL;

    /* If the file mode is writable, skip all the bundle stuff because generally the bundle is read-only. */
    if(strcmp("r", mode) && strcmp("rb", mode)) {
        return fopen(file, mode);
    }

    NSFileManager* file_manager = [NSFileManager defaultManager];
    NSString* resource_path = [[NSBundle mainBundle] resourcePath];

    NSString* ns_string_file_component = [file_manager stringWithFileSystemRepresentation:file length:strlen(file)];

    NSString* full_path_with_file_to_try = [resource_path stringByAppendingPathComponent:ns_string_file_component];"""

new = """    FILE* fp = NULL;
    NSFileManager* file_manager = [NSFileManager defaultManager];
    NSString* resource_path = [[NSBundle mainBundle] resourcePath];
    NSString* ns_string_file_component = [file_manager stringWithFileSystemRepresentation:file length:strlen(file)];
    NSString* full_path_with_file_to_try = [resource_path stringByAppendingPathComponent:ns_string_file_component];

    /* If the file mode is writable, skip all the bundle stuff because generally the bundle is read-only. */
    if(strcmp("r", mode) && strcmp("rb", mode)) {
        return fopen(file, mode);
    }"""

with open(path) as f:
    content = f.read()

if new in content:
    print("Already patched, nothing to do.")
elif old in content:
    content = content.replace(old, new, 1)
    with open(path, "w") as f:
        f.write(content)
    print("Patched successfully.")
else:
    raise SystemExit(
        "ERROR: expected text not found in " + path +
        " - upstream SDL2 source may have changed, patch needs updating."
    )
