import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

/// An error returned by the Vargani API, already in the user's language.
class ApiException implements Exception {
  ApiException(this.statusCode, this.code, this.message, [this.details = const {}]);

  final int statusCode;
  final String code;
  final String message;
  final Map<String, dynamic> details;

  /// First message for a field, following nested paths such as `lines.0.amount`.
  String? fieldError(String path) {
    dynamic node = details;
    for (final part in path.split('.')) {
      if (node is Map) {
        node = node[part];
      } else if (node is List) {
        final i = int.tryParse(part);
        node = (i != null && i < node.length) ? node[i] : null;
      } else {
        return null;
      }
    }
    if (node is List && node.isNotEmpty) {
      final first = node.first;
      if (first is Map) return first['message']?.toString();
      return first.toString();
    }
    return null;
  }

  @override
  String toString() => message;
}

/// Where tokens are kept between app starts.
abstract class TokenStore {
  Future<String?> readRefresh();
  Future<void> writeRefresh(String? token);
}

class MemoryTokenStore implements TokenStore {
  String? _token;
  @override
  Future<String?> readRefresh() async => _token;
  @override
  Future<void> writeRefresh(String? token) async => _token = token;
}

/// Thin client over `/api/v1/`. Business rules stay on the server; this only adds
/// headers, refreshes the access token once on 401 and turns error bodies into [ApiException].
class ApiClient {
  ApiClient({required this.baseUrl, required this.tokens, http.Client? httpClient})
    : _http = httpClient ?? http.Client();

  String baseUrl; // e.g. https://api.example.in  (no trailing slash, no /api/v1)
  final TokenStore tokens;
  final http.Client _http;

  String? accessToken;
  String? orgId;
  String language = 'en';

  /// Called when the session cannot be refreshed and the user must log in again.
  void Function()? onSessionExpired;

  Uri uri(String path, [Map<String, String?>? query]) {
    final q = <String, String>{};
    query?.forEach((k, v) {
      if (v != null && v.isNotEmpty) q[k] = v;
    });
    final base = baseUrl.endsWith('/') ? baseUrl.substring(0, baseUrl.length - 1) : baseUrl;
    return Uri.parse('$base/api/v1$path').replace(queryParameters: q.isEmpty ? null : q);
  }

  Map<String, String> headers({bool json = true, Map<String, String>? extra}) => {
    if (json) 'Content-Type': 'application/json',
    'Accept-Language': language,
    'X-Client-Type': 'app',
    if (accessToken != null) 'Authorization': 'Bearer $accessToken',
    'X-Organization-ID': ?orgId,
    ...?extra,
  };

  Future<dynamic> get(String path, {Map<String, String?>? query}) => _send('GET', path, query: query);

  Future<dynamic> post(String path, [Object? body, Map<String, String>? extraHeaders]) =>
      _send('POST', path, body: body ?? const {}, extraHeaders: extraHeaders);

  Future<dynamic> patch(String path, Object body) => _send('PATCH', path, body: body);

  /// Uploads one file as multipart form data (field `file`), e.g. a bill photo.
  Future<dynamic> upload(String path, Uint8List bytes, String filename) async {
    Future<http.Response> send() {
      final req = http.MultipartRequest('POST', uri(path))
        ..headers.addAll(headers(json: false))
        ..files.add(http.MultipartFile.fromBytes('file', bytes, filename: filename));
      return _http.send(req).then(http.Response.fromStream);
    }

    var res = await send();
    if (res.statusCode == 401 && await refresh()) res = await send();
    if (res.statusCode >= 400) throw _error(res);
    return res.bodyBytes.isEmpty ? null : jsonDecode(utf8.decode(res.bodyBytes));
  }

  Future<dynamic> delete(String path) => _send('DELETE', path);

  Future<Uint8List> getBytes(String path, {Map<String, String?>? query}) async {
    var res = await _raw('GET', uri(path, query), null, null);
    if (res.statusCode == 401 && await refresh()) {
      res = await _raw('GET', uri(path, query), null, null);
    }
    if (res.statusCode >= 400) throw _error(res);
    return res.bodyBytes;
  }

  Future<dynamic> _send(
    String method,
    String path, {
    Map<String, String?>? query,
    Object? body,
    Map<String, String>? extraHeaders,
  }) async {
    final u = uri(path, query);
    var res = await _raw(method, u, body, extraHeaders);
    if (res.statusCode == 401 && accessToken != null && !path.startsWith('/auth/')) {
      if (await refresh()) {
        res = await _raw(method, u, body, extraHeaders);
      } else {
        onSessionExpired?.call();
      }
    }
    if (res.statusCode >= 400) throw _error(res);
    if (res.bodyBytes.isEmpty) return null;
    return jsonDecode(utf8.decode(res.bodyBytes));
  }

  Future<http.Response> _raw(String method, Uri u, Object? body, Map<String, String>? extra) {
    final req = http.Request(method, u)..headers.addAll(headers(extra: extra));
    if (body != null) req.body = jsonEncode(body);
    return _http.send(req).then(http.Response.fromStream);
  }

  ApiException _error(http.Response res) {
    try {
      final data = jsonDecode(utf8.decode(res.bodyBytes));
      final err = data['error'] as Map<String, dynamic>;
      return ApiException(
        res.statusCode,
        err['code']?.toString() ?? 'error',
        err['message']?.toString() ?? 'Error',
        (err['details'] as Map?)?.cast<String, dynamic>() ?? {},
      );
    } catch (_) {
      return ApiException(res.statusCode, 'http_${res.statusCode}', 'Request failed (${res.statusCode}).');
    }
  }

  Future<void> saveSession(Map<String, dynamic> auth) async {
    accessToken = auth['access'] as String?;
    await tokens.writeRefresh(auth['refresh'] as String?);
  }

  bool _refreshing = false;

  /// Swaps the stored refresh token for a new pair (tokens rotate on the server).
  Future<bool> refresh() async {
    if (_refreshing) return false;
    _refreshing = true;
    try {
      final rt = await tokens.readRefresh();
      if (rt == null) return false;
      final res = await _http.post(
        uri('/auth/refresh/'),
        headers: {'Content-Type': 'application/json', 'X-Client-Type': 'app'},
        body: jsonEncode({'refresh': rt}),
      );
      if (res.statusCode != 200) {
        accessToken = null;
        await tokens.writeRefresh(null);
        return false;
      }
      await saveSession(jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
      return true;
    } catch (_) {
      return false;
    } finally {
      _refreshing = false;
    }
  }

  Future<void> logout() async {
    final rt = await tokens.readRefresh();
    try {
      if (rt != null) await post('/auth/logout/', {'refresh': rt});
    } catch (_) {
      // The local session is cleared either way.
    }
    accessToken = null;
    orgId = null;
    await tokens.writeRefresh(null);
  }
}

/// Lists from the API are either plain arrays or `{count, next, results}` pages.
List<Map<String, dynamic>> resultsOf(dynamic data) {
  final list = data is Map ? (data['results'] as List? ?? const []) : (data as List? ?? const []);
  return list.cast<Map>().map((e) => e.cast<String, dynamic>()).toList();
}
