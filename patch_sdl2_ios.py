"""Patch SDL2's SDL_rwopsbundlesupport.m for -Werror=declaration-after-statement.

Run from the repository root. Idempotent: safe to run even if already patched.
"""

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

    /* If the file mode is writable, skip all the bundle stuff because generally the bundle is read-only. */
    if(strcmp("r", mode) && strcmp("rb", mode)) {
        return fopen(file, mode);
    }

    NSString* ns_string_file_component = [file_manager stringWithFileSystemRepresentation:file length:strlen(file)];

    NSString* full_path_with_file_to_try = [resource_path stringByAppendingPathComponent:ns_string_file_component];"""

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
