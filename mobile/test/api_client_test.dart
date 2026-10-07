import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:vargani_app/api/api_client.dart';

void main() {
  test('sends tenant, language and app headers', () async {
    late http.Request seen;
    final api = ApiClient(
      baseUrl: 'https://api.example.in/',
      tokens: MemoryTokenStore(),
      httpClient: MockClient((r) async {
        seen = r;
        return http.Response('{"ok":true}', 200);
      }),
    )
      ..accessToken = 'A'
      ..orgId = 'org-1'
      ..language = 'mr';
    await api.post('/collections/', {'x': 1}, {'Idempotency-Key': 'k-1'});
    expect(seen.url.toString(), 'https://api.example.in/api/v1/collections/');
    expect(seen.headers['Authorization'], 'Bearer A');
    expect(seen.headers['X-Organization-ID'], 'org-1');
    expect(seen.headers['Accept-Language'], 'mr');
    expect(seen.headers['X-Client-Type'], 'app');
    expect(seen.headers['Idempotency-Key'], 'k-1');
  });

  test('refreshes once on 401, stores the rotated token and retries', () async {
    final store = MemoryTokenStore();
    await store.writeRefresh('R1');
    var calls = 0;
    final api = ApiClient(
      baseUrl: 'https://api.example.in',
      tokens: store,
      httpClient: MockClient((r) async {
        if (r.url.path.endsWith('/auth/refresh/')) {
          expect(jsonDecode(r.body)['refresh'], 'R1');
          return http.Response('{"access":"A2","refresh":"R2"}', 200);
        }
        calls++;
        return r.headers['Authorization'] == 'Bearer A2'
            ? http.Response('{"unread":3}', 200)
            : http.Response('{"error":{"code":"not_authenticated","message":"x","details":{}}}', 401);
      }),
    )..accessToken = 'A1';
    final r = await api.get('/notifications/unread-count/');
    expect(r['unread'], 3);
    expect(calls, 2);
    expect(api.accessToken, 'A2');
    expect(await store.readRefresh(), 'R2');
  });

  test('a failed refresh ends the session', () async {
    final store = MemoryTokenStore();
    await store.writeRefresh('old');
    var expired = false;
    final api = ApiClient(
      baseUrl: 'https://x',
      tokens: store,
      httpClient: MockClient((r) async => http.Response(
          '{"error":{"code":"token_not_valid","message":"Session expired.","details":{}}}', 401)),
    )
      ..accessToken = 'A'
      ..onSessionExpired = () => expired = true;
    await expectLater(api.get('/me/'), throwsA(isA<ApiException>()));
    expect(expired, isTrue);
    expect(await store.readRefresh(), isNull);
  });

  test('error bodies become ApiException with nested field errors', () async {
    final api = ApiClient(
      baseUrl: 'https://x',
      tokens: MemoryTokenStore(),
      httpClient: MockClient((r) async => http.Response(
          jsonEncode({
            'error': {
              'code': 'validation_error',
              'message': 'Some fields are invalid.',
              'details': {
                'lines': [
                  {'amount': [{'code': 'invalid', 'message': 'Amount must be more than zero.'}]}
                ]
              }
            }
          }),
          400)),
    );
    try {
      await api.post('/collections/', {});
      fail('should throw');
    } on ApiException catch (e) {
      expect(e.statusCode, 400);
      expect(e.message, 'Some fields are invalid.');
      expect(e.fieldError('lines.0.amount'), 'Amount must be more than zero.');
      expect(e.fieldError('lines.1.amount'), isNull);
    }
  });

  test('resultsOf reads both pages and plain lists', () {
    expect(resultsOf({'count': 1, 'results': [{'a': 1}]}), [{'a': 1}]);
    expect(resultsOf([{'b': 2}]), [{'b': 2}]);
  });
}
