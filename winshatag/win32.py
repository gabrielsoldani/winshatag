# Copyright (c) 2021 Gabriel Soldani
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
This module is a wrapper for Win32 file writing APIs. 

Since NTFS alternate data streams share file attributes such as the last
modification date, we need to be able to overwrite the modification date when
we're tagging the file, but at the time of this writing, os.utime doesn't
support file descriptors on Windows. Closing the file and then reopening to
overwrite the modification date would introduce a race condition. In order to
do both operations on the same open file descriptor, we need direct access to
Win32 APIs.
"""

import os
from datetime import datetime, time
from typing import Union

from ctypes import WinDLL, get_last_error, WinError, create_string_buffer, sizeof, byref, c_char
from ctypes.wintypes import LPCWSTR, DWORD, LPVOID, HANDLE, BOOL, LPCVOID, LPDWORD, LPFILETIME, FILETIME
LPSECURITY_ATTRIBUTES = LPVOID
LPOVERLAPPED = LPVOID
NULL = None

kernel32 = WinDLL('kernel32', use_last_error=True)

CreateFileW = kernel32.CreateFileW
CreateFileW.restype = HANDLE
CreateFileW.argtypes = (
    LPCWSTR,
    DWORD,
    DWORD,
    LPSECURITY_ATTRIBUTES,
    DWORD,
    DWORD,
    HANDLE
)

FILE_READ_DATA = 1
FILE_READ_ATTRIBUTES = 128
FILE_WRITE_DATA = 2
FILE_WRITE_ATTRIBUTES = 256

FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
FILE_SHARE_DELETE = 4

CREATE_ALWAYS = 2
OPEN_EXISTING = 3

FILE_FLAG_SEQUENTIAL_SCAN = 0x08000000

INVALID_HANDLE_VALUE = HANDLE(-1).value

CloseHandle = kernel32.CloseHandle
CloseHandle.restype = BOOL
CloseHandle.argtypes = (
    HANDLE,
)

FALSE = BOOL(0).value

ReadFile = kernel32.ReadFile
ReadFile.restype = BOOL
ReadFile.argtypes = (
    HANDLE,
    LPVOID,
    DWORD,
    LPDWORD,
    LPOVERLAPPED,
)

WriteFile = kernel32.WriteFile
WriteFile.restype = BOOL
WriteFile.argtypes = (
    HANDLE,
    LPCVOID,
    DWORD,
    LPDWORD,
    LPOVERLAPPED,
)

GetFileTime = kernel32.GetFileTime
GetFileTime.restype = BOOL
GetFileTime.argtypes = (
    HANDLE,
    LPFILETIME,
    LPFILETIME,
    LPFILETIME,
)

SetFileTime = kernel32.SetFileTime
SetFileTime.restype = BOOL
SetFileTime.argtypes = (
    HANDLE,
    LPFILETIME,
    LPFILETIME,
    LPFILETIME,
)


__NANOSECONDS_BETWEEN_EPOCHS = 11644473600 * 1000000000


def FILETIME_to_time_ns(filetime):
    """
    Converts FILETIME to time_ns.

    FILETIME counts 100-nanosecond intervals since January 1, 1601.
    time_ns counts 1-nanosecond intervals since January 1, 1970.

    Reference: https://docs.microsoft.com/en-us/windows/win32/api/minwinbase/ns-minwinbase-filetime
    """
    filetime = (filetime.dwLowDateTime | (filetime.dwHighDateTime << 32))
    return filetime * 100 - __NANOSECONDS_BETWEEN_EPOCHS


def time_ns_to_FILETIME(time_ns):
    """
    Converts time_ns to FILETIME.

    FILETIME counts 100-nanosecond intervals since January 1, 1601.
    time_ns counts 1-nanosecond intervals since January 1, 1970.

    Reference: https://docs.microsoft.com/en-us/windows/win32/api/minwinbase/ns-minwinbase-filetime
    """
    filetime = (time_ns + __NANOSECONDS_BETWEEN_EPOCHS) // 100
    return FILETIME(filetime & 0xFFFFFFFF, filetime >> 32)


class Win32File(object):
    def __init__(self, filename, mode):
        filename = os.path.abspath(str(filename))
        if mode == 'rb':
            hFile = CreateFileW(
                filename,
                FILE_READ_DATA | FILE_READ_ATTRIBUTES,
                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                NULL,
                OPEN_EXISTING,
                FILE_FLAG_SEQUENTIAL_SCAN,
                NULL
            )
        elif mode == 'wb':
            hFile = CreateFileW(
                filename,
                FILE_WRITE_DATA | FILE_WRITE_ATTRIBUTES,
                0,
                NULL,
                CREATE_ALWAYS,
                0,
                NULL
            )
        else:
            raise NotImplementedError(f'mode {mode}')

        if hFile == INVALID_HANDLE_VALUE:
            raise WinError(get_last_error())

        self._hFile = hFile

    def read(self):
        bytearr = bytearray()
        bytes_read = DWORD(0)
        buf = create_string_buffer(4096)
        while True:
            if ReadFile(self._hFile, buf, sizeof(buf), byref(bytes_read), NULL) == FALSE:
                raise WinError(get_last_error())
            if bytes_read.value == 0:
                break
            buf.value[0:bytes_read.value]
            bytearr.extend(buf.value[:bytes_read.value])
        return bytearr

    def write(self, data: Union[bytes, bytearray]):
        bytearr = bytearray(data)
        bytes_written = DWORD(0)
        while True:
            chararr = (c_char*len(bytearr)).from_buffer(bytearr)
            if WriteFile(self._hFile, chararr, len(bytearr), byref(bytes_written), None) == FALSE:
                raise WinError(get_last_error())
            bytearr = bytearr[bytes_written.value:]
            if len(bytearr) == 0:
                break

    def get_mdate_ns(self):
        filetime = FILETIME(0xFFFFFFFF, 0xFFFFFFFF)

        if GetFileTime(self._hFile, NULL, NULL, byref(filetime)) == FALSE:
            raise WinError(get_last_error())

        return FILETIME_to_time_ns(filetime)

    def touch(self, time_ns=None):
        if time_ns is None:
            time_ns = time.time_ns()

        filetime = time_ns_to_FILETIME(time_ns)

        if SetFileTime(self._hFile, NULL, filetime, filetime) == FALSE:
            raise WinError(get_last_error())

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if CloseHandle(self._hFile) == FALSE:
            raise WinError(get_last_error())
