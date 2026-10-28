import 'dart:js_interop';
import 'dart:typed_data';

import 'package:web/web.dart' as web;

/// In a browser, open the PDF in a new tab.
Future<void> openPdfBytes(Uint8List bytes, String fileName) async {
  final blob = web.Blob([bytes.toJS].toJS, web.BlobPropertyBag(type: 'application/pdf'));
  final url = web.URL.createObjectURL(blob);
  web.window.open(url, '_blank');
}

/// In a browser, save the file to Downloads.
Future<void> openFileBytes(Uint8List bytes, String fileName, String mimeType) async {
  final blob = web.Blob([bytes.toJS].toJS, web.BlobPropertyBag(type: mimeType));
  final link = web.HTMLAnchorElement()
    ..href = web.URL.createObjectURL(blob)
    ..download = fileName;
  link.click();
}
