import 'dart:io';
import 'dart:typed_data';

import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

/// Saves the PDF to the app's temporary folder and opens it in the phone's PDF viewer.
Future<void> openPdfBytes(Uint8List bytes, String fileName) => openFileBytes(bytes, fileName, 'application/pdf');

/// Saves the file to the app's temporary folder and opens it in an app that reads it (PDF viewer, Sheets,
/// Excel), from where it can be shared or saved.
Future<void> openFileBytes(Uint8List bytes, String fileName, String mimeType) async {
  final dir = await getTemporaryDirectory();
  final safe = fileName.replaceAll(RegExp(r'[^A-Za-z0-9._-]'), '_');
  final file = File('${dir.path}/$safe');
  await file.writeAsBytes(bytes, flush: true);
  final result = await OpenFilex.open(file.path, type: mimeType);
  if (result.type != ResultType.done) throw Exception(result.message);
}
