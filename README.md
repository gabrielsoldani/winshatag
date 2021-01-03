# About winshatag

With winshatag, you can detect silent data corruption on Windows. It writes the last modification date and time and the sha256 checksum of a file into [NTFS alternate data streams](https://docs.microsoft.com/en-us/archive/blogs/askcore/alternate-data-streams-in-ntfs). They'll persist if the file is edited, copied or moved. So, when you run winshatag again, it compares the file's actual modification date with the stored modification date from when winshatag was last ran. If they match, it calculates the file's checksum and compares it with the stored checksum. If they're different, the file was silently corrupted. winshatag will keep the alternate data streams up to date and warn you if the file is corrupt.

## Inspiration

winshatag is an adaptation of [Jakob Unterwurzacher's cshatag](https://github.com/rfjakob/cshatag) and [Maxime Augier's shatag](https://github.com/maugier/shatag) for NTFS on Windows.
