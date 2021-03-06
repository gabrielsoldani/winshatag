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

import argparse
import os
import hashlib
import sys

from .win32 import Win32File

CHUNK_SIZE = 4096 * 2

NANOSECONDS_IN_A_SECOND = 1_000_000_000


def formatTimestamp(time_ns):
    if time_ns == None:
        return None

    seconds = time_ns // NANOSECONDS_IN_A_SECOND
    nanoseconds = time_ns % NANOSECONDS_IN_A_SECOND
    return "{0}.{1:09d}".format(seconds, nanoseconds)


def getStoredSha256(filename):
    try:
        with open(filename + ':shatag.sha256:$DATA', 'r') as f:
            return f.read().lower()
    except FileNotFoundError:
        return None


def getStoredTimestamp(filename):
    try:
        with open(filename + ':shatag.ts:$DATA', 'r') as f:
            seconds, nanoseconds = tuple(map(int, f.read().split('.')))
            return seconds * NANOSECONDS_IN_A_SECOND + nanoseconds
    except FileNotFoundError:
        return None


def writeSha256(filename, sha256):
    with Win32File(filename + ':shatag.sha256:$DATA', 'wb') as f:
        return f.write(sha256.encode('ascii'))


def writeTimestamp(filename, time_ns):
    with Win32File(filename + ':shatag.ts:$DATA', 'wb') as f:
        f.write(formatTimestamp(time_ns).encode('ascii'))
        f.touch(time_ns)


def getActualTimestamp(filename):
    result = os.stat(filename)
    return result.st_mtime_ns


def getActualSha256(filename):
    hash = hashlib.sha256()
    with open(filename, 'rb') as f:
        while chunk := f.read(CHUNK_SIZE):
            hash.update(chunk)
    return hash.hexdigest().lower()


parser = argparse.ArgumentParser(
    description='Detects silent data changes by storing the file\'s checksum and modification date into NTFS ADS.')
parser.add_argument("filename", metavar='FILE', help='file to checksum')


def main(argv=None):
    args = parser.parse_args(argv)

    if args.filename == []:
        parser.print_usage()
        return 1

    filename = os.path.abspath(args.filename)

    stored_ts = getStoredTimestamp(filename)
    stored_sha256 = getStoredSha256(filename)
    actual_ts = getActualTimestamp(filename)
    actual_sha256 = getActualSha256(filename)

    must_update = False
    is_corrupt = False

    if stored_ts == actual_ts:
        # Modified timestamps are the same.
        # Compare the hash.
        if stored_sha256 != actual_sha256:
            # Hashes are different.
            # Perhaps the file was modified while we were reading it
            actual_ts = getActualTimestamp(filename)
            if stored_ts == actual_ts:
                print("Error: corrupt file", filename, file=sys.stderr)
                print("<corrupt>", filename)
                print(" stored:", stored_sha256, formatTimestamp(stored_ts))
                print(" actual:", actual_sha256, formatTimestamp(actual_ts))
                is_corrupt = True
                # must_update = True
        else:
            # Hashes are the same.
            print("<ok>", filename)
    else:
        # Modified timestamps are different.
        print("<outdated>", filename)
        print(" stored:", stored_sha256, formatTimestamp(stored_ts))
        print(" actual:", actual_sha256, formatTimestamp(actual_ts))
        must_update = True

    if must_update:
        try:
            writeSha256(filename, actual_sha256)
            writeTimestamp(filename, actual_ts)
        except Exception as e:
            print("Error: could not write NTFS ADS to file", filename, e)
            return 4

    if is_corrupt:
        return 5
    else:
        return 0
