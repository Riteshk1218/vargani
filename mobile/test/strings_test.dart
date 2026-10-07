import 'package:flutter_test/flutter_test.dart';
import 'package:vargani_app/l10n/strings.dart';

void main() {
  test('Marathi and Hindi translate every label', () {
    expect(missingKeys('mr'), isEmpty);
    expect(missingKeys('hi'), isEmpty);
  });

  test('placeholders are filled and unknown languages fall back to English', () {
    expect(tr('en', 'code_sent', {'dest': '98******22'}), 'Code sent to 98******22');
    expect(tr('mr', 'collect'), 'वसुली');
    expect(tr('xx', 'collect'), 'Collect');
  });
}
