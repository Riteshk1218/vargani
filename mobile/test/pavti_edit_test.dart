import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:vargani_app/api/api_client.dart';
import 'package:vargani_app/screens/receipt_screen.dart';
import 'package:vargani_app/state/app_state.dart';
import 'package:vargani_app/widgets/common.dart';

/// The person who created a pavti edits its amount in place: the same pavti, the same number.
void main() {
  testWidgets('creator edits the pavti amount and the receipt keeps its number', (tester) async {
    SharedPreferences.setMockInitialValues({});
    final edits = <Map<String, dynamic>>[];
    var amount = '500.00';
    http.Response json(Object body) =>
        http.Response.bytes(utf8.encode(jsonEncode(body)), 200, headers: {'content-type': 'application/json'});
    Future<http.Response> handle(http.Request r) async {
      final p = r.url.path.replaceFirst('/api/v1', '');
      switch ((r.method, p)) {
        case ('GET', '/receipts/rc-1/'):
          return json({
            'id': 'rc-1', 'receipt_number': 'GC-2026-00007', 'status': 'issued', 'amount': amount, 'payment': 'pay-1',
            'can_edit': true, 'created_by_name': 'Kiran', 'logo_url': null,
            'snapshot': {
              'organization': {'name': 'Demo Mandal'},
              'person': {'name': 'Sunita More'},
              'lines': [{'contribution_type': 'Ganesh Vargani', 'amount': amount}],
              'total': amount, 'mode': 'cash',
            },
          });
        case ('GET', '/payments/pay-1/'):
          return json({
            'id': 'pay-1', 'payer_name': 'Sunita More', 'amount': amount, 'mode': 'cash', 'reference_number': '',
            'notes': '', 'can_edit': true,
            'lines': [{'contribution_type': 'ct-1', 'contribution_type_name': 'Ganesh Vargani', 'period_month': null,
              'amount': amount, 'notes': ''}],
          });
        case ('POST', '/payments/pay-1/edit/'):
          final body = (jsonDecode(r.body) as Map).cast<String, dynamic>();
          edits.add(body);
          amount = '${(body['lines'] as List).first['amount']}.00';
          return json({'id': 'pay-1', 'amount': amount});
      }
      return http.Response('{}', 404);
    }

    final state = AppState(
      api: ApiClient(baseUrl: 'https://api.test', tokens: MemoryTokenStore(), httpClient: MockClient(handle)),
      prefs: await SharedPreferences.getInstance(),
    );
    await tester.binding.setSurfaceSize(const Size(420, 1400));
    await tester.pumpWidget(
      AppScope(state: state, child: const MaterialApp(home: ReceiptScreen(receiptId: 'rc-1'))),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('receipt-edit')));
    await tester.pumpAndSettle();
    expect(find.textContaining('GC-2026-00007'), findsOneWidget);
    await tester.enterText(find.byKey(const Key('edit-amount-0')), '750');
    await tester.tap(find.byKey(const Key('edit-save')));
    await tester.pumpAndSettle();

    expect(edits, [
      {
        'lines': [
          {'contribution_type': 'ct-1', 'period_month': null, 'amount': '750'},
        ],
      },
    ]);
    // Back on the same pavti, which now shows the new amount.
    expect(find.text('Receipt no. GC-2026-00007'), findsOneWidget);
    expect(find.text('₹750'), findsWidgets);
  });
}
