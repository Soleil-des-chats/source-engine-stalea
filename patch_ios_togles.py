#!/usr/bin/env python3
"""
Patch script for the three iOS/togles build failures:
  1. ilaunchermgr.h always pulling in desktop `togl` headers instead of `togles`
  2. togles/rendermechanism.h always including desktop <GL/gl.h>/<GL/glext.h>
  3. sdlmgr.cpp always including EGL headers on iOS, even without ANGLE

Usage:
    python3 patch_ios_togles.py [path-to-repo-root]

If no path is given, the current directory is used. Safe to re-run
(each patch checks whether it's already applied and skips if so).
Original files are backed up alongside with a .orig suffix the first
time they're touched.
"""

import sys
import os

REPO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')


def backup(path):
    bak = path + '.orig'
    if not os.path.exists(bak):
        with open(path, 'r') as f:
            data = f.read()
        with open(bak, 'w') as f:
            f.write(data)


def patch_file(rel_path, old, new, label):
    path = os.path.join(REPO, rel_path)
    if not os.path.exists(path):
        print(f'[SKIP] {label}: file not found at {path}')
        return False

    with open(path, 'r') as f:
        content = f.read()

    if new in content:
        print(f'[OK]   {label}: already patched')
        return True

    if old not in content:
        print(f'[FAIL] {label}: expected original text not found — '
              f'file may already differ from what this script expects. '
              f'Check {rel_path} manually.')
        return False

    backup(path)
    content = content.replace(old, new, 1)
    with open(path, 'w') as f:
        f.write(content)
    print(f'[PATCHED] {label}')
    return True


def main():
    ok = True

    # ------------------------------------------------------------------
    # 1. public/appframework/ilaunchermgr.h
    #    Select togles vs togl headers based on the TOGLES define, same
    #    pattern already used elsewhere in the codebase.
    # ------------------------------------------------------------------
    old1 = '''#if defined( DX_TO_GL_ABSTRACTION )

#include "togl/linuxwin/glmgrbasics.h"
#include "togl/linuxwin/glmdisplay.h"

class GLMDisplayDB;
class CShowPixelsParams;
#endif'''

    new1 = '''#if defined( DX_TO_GL_ABSTRACTION )

#ifdef TOGLES
#include "togles/linuxwin/glmgrbasics.h"
#include "togles/linuxwin/glmdisplay.h"
#else
#include "togl/linuxwin/glmgrbasics.h"
#include "togl/linuxwin/glmdisplay.h"
#endif

class GLMDisplayDB;
class CShowPixelsParams;
#endif'''

    ok &= patch_file(
        'public/appframework/ilaunchermgr.h',
        old1, new1,
        'ilaunchermgr.h (togl -> togles header selection)'
    )

    # ------------------------------------------------------------------
    # 2. public/togles/rendermechanism.h
    #    Use Apple's OpenGLES headers on iOS instead of the desktop-style
    #    GL/gl.h + GL/glext.h stubs, which conflict with the real ES2 API.
    # ------------------------------------------------------------------
    old2 = '''#undef PROTECTED_THINGS_ENABLE

#include <GL/gl.h>
#include <GL/glext.h>

#include "tier0/basetypes.h"'''

    new2 = '''#undef PROTECTED_THINGS_ENABLE

#if defined(IOS) && !defined(ANGLE)
#include <OpenGLES/ES2/gl.h>
#include <OpenGLES/ES2/glext.h>
#ifndef GL_HALF_FLOAT
#define GL_HALF_FLOAT GL_HALF_FLOAT_OES
#endif
#else
#include <GL/gl.h>
#include <GL/glext.h>
#endif

#include "tier0/basetypes.h"'''

    ok &= patch_file(
        'public/togles/rendermechanism.h',
        old2, new2,
        'togles/rendermechanism.h (use OpenGLES headers on iOS)'
    )

    # ------------------------------------------------------------------
    # 3. appframework/sdlmgr.cpp
    #    Only pull in EGL headers on iOS when building with ANGLE; native
    #    OpenGLES on iOS uses EAGLContext and has no EGL/egl.h at all.
    # ------------------------------------------------------------------
    old3 = '''#if TOGLES && !IOS
#include <EGL/egl.h>
#endif
#if IOS
#include <dlfcn.h>
#include "EGL/egl.h"
#include "EGL/eglext.h"
#include "EGL/eglext_angle.h"
#include "SDL2/SDL_rect.h"
#include "SDL2/sdl_video.h"
#include "SDL2/SDL_syswm.h"
#endif'''

    new3 = '''#if TOGLES && !IOS
#include <EGL/egl.h>
#endif
#if IOS
#include <dlfcn.h>
#include "SDL2/SDL_rect.h"
#include "SDL2/sdl_video.h"
#include "SDL2/SDL_syswm.h"
#if defined(ANGLE)
#include "EGL/egl.h"
#include "EGL/eglext.h"
#include "EGL/eglext_angle.h"
#endif
#endif'''

    ok &= patch_file(
        'appframework/sdlmgr.cpp',
        old3, new3,
        'sdlmgr.cpp (only include EGL headers on iOS when using ANGLE)'
    )

    # ------------------------------------------------------------------
    # 4. public/togles/linuxwin/glentrypoints.h
    #    APIENTRY is only ever defined inside the desktop GL/glext.h stubs,
    #    which fix #2 correctly stopped including on iOS. The OSX branch
    #    here already avoids needing _APIENTRY at all (Apple platforms
    #    don't use that calling-convention macro) but was never extended
    #    to cover IOS, so iOS fell into the _APIENTRY/APIENTRY branch and
    #    APIENTRY is now nowhere defined.
    # ------------------------------------------------------------------
    old4 = '#ifdef OSX\n#define GL_EXT(x,glmajor,glminor) bool m_bHave_##x;'
    new4 = '#if defined(OSX) || defined(IOS)\n#define GL_EXT(x,glmajor,glminor) bool m_bHave_##x;'

    ok &= patch_file(
        'public/togles/linuxwin/glentrypoints.h',
        old4, new4,
        'glentrypoints.h (treat IOS like OSX for the _APIENTRY macro)'
    )

    print()
    if ok:
        print('All patches applied (or already present). '
              'Backups saved as *.orig next to each modified file.')
    else:
        print('One or more patches could not be applied — see [FAIL]/[SKIP] '
              'lines above and check those files by hand.')
        sys.exit(1)


if __name__ == '__main__':
    main()
