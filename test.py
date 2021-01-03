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

import os
import winshatag

print("*** Testing new empty file ***")
filename = 'foo.txt'

try:
    os.unlink(filename)
except FileNotFoundError:
    pass

open(filename, 'w').close()

assert winshatag.getStoredTimestamp(filename) == None
assert winshatag.getStoredSha256(filename) == None

exitcode = winshatag.main([filename])
assert exitcode == 0
assert winshatag.getStoredSha256(
    filename) == 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'


print("*** Testing new 100-byte file ***")
filename = 'foo.txt'

try:
    os.unlink(filename)
except FileNotFoundError:
    pass

with open(filename, 'wb') as f:
    f.write(bytes(range(100)))

assert winshatag.getStoredTimestamp(filename) == None
assert winshatag.getStoredSha256(filename) == None

exitcode = winshatag.main([filename])
assert exitcode == 0
assert winshatag.getStoredSha256(
    filename) == 'bce0aff19cf5aa6a7469a30d61d04e4376e4bbf6381052ee9e7f33925c954d52'

print("*** Modifying date in new 100-byte file ***")
ts = 1909669684252460189
os.utime(filename, ns=(ts, ts))
ts = int(os.stat(filename).st_mtime)

exitcode = winshatag.main([filename])
assert exitcode == 0
assert winshatag.getStoredTimestamp(filename) == ts
print(winshatag.getActualTimestamp(filename))

print("*** No changes made to file ***")
exitcode = winshatag.main([filename])
assert exitcode == 0

print("*** Silently corrupting 100-byte file ***")
with open(filename, 'ab+') as f:
    f.seek(0)
    f.write(bytes(range(0, 200, 2)))
os.utime(filename, times=(ts, ts))

exitcode = winshatag.main([filename])
assert exitcode == 5

print("Tests passed.")

os.unlink('foo.txt')
