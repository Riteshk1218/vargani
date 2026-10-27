import 'dart:typed_data';

Future<void> openPdfBytes(Uint8List bytes, String fileName) async =>
    throw UnsupportedError('Opening files is not supported on this platform.');

Future<void> openFileBytes(Uint8List bytes, String fileName, String mimeType) async =>
    throw UnsupportedError('Opening files is not supported on this platform.');
