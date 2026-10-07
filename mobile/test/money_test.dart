import 'package:flutter_test/flutter_test.dart';
import 'package:vargani_app/util/money.dart';

void main() {
  test('Indian grouping keeps paise and never uses floating point', () {
    expect(formatInr('0.00'), '₹0');
    expect(formatInr('500.00'), '₹500');
    expect(formatInr('1100.50'), '₹1,100.50');
    expect(formatInr('110000.50'), '₹1,10,000.50');
    expect(formatInr('12345678.05'), '₹1,23,45,678.05');
    expect(formatInr('-2600.00'), '-₹2,600');
    expect(formatInr(null), '₹0');
  });

  test('amount input is validated and normalised for the API', () {
    expect(normaliseAmount('500'), '500.00');
    expect(normaliseAmount(' 750.5 '), '750.50');
    expect(normaliseAmount('1,000'), '1000.00');
    expect(normaliseAmount('0'), isNull);
    expect(normaliseAmount('-5'), isNull);
    expect(normaliseAmount('12.345'), isNull);
    expect(normaliseAmount('abc'), isNull);
  });
}
