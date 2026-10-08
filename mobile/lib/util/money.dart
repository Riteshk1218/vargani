/// Money arrives from the API as strings such as "110000.50". It is shown, never
/// used for arithmetic, so it stays a string and only gets ₹ and Indian grouping.
String formatInr(String? amount) {
  if (amount == null || amount.isEmpty) return '₹0';
  var s = amount.trim();
  final negative = s.startsWith('-');
  if (negative) s = s.substring(1);
  final parts = s.split('.');
  final whole = parts[0].isEmpty ? '0' : parts[0];
  var frac = parts.length > 1 ? parts[1] : '';
  if (RegExp(r'^0*$').hasMatch(frac)) frac = '';
  String grouped;
  if (whole.length <= 3) {
    grouped = whole;
  } else {
    final last3 = whole.substring(whole.length - 3);
    var rest = whole.substring(0, whole.length - 3);
    final groups = <String>[];
    while (rest.length > 2) {
      groups.insert(0, rest.substring(rest.length - 2));
      rest = rest.substring(0, rest.length - 2);
    }
    if (rest.isNotEmpty) groups.insert(0, rest);
    grouped = '${groups.join(',')},$last3';
  }
  if (frac.length == 1) frac = '${frac}0';
  return '${negative ? '-' : ''}₹$grouped${frac.isEmpty ? '' : '.$frac'}';
}

/// Validates what a collector typed and returns it in the API's format ("500.00"), or null.
String? normaliseAmount(String input) {
  final s = input.trim().replaceAll(',', '');
  final m = RegExp(r'^(\d{1,10})(?:\.(\d{1,2}))?$').firstMatch(s);
  if (m == null) return null;
  final whole = int.parse(m.group(1)!).toString();
  final frac = (m.group(2) ?? '').padRight(2, '0');
  if (whole == '0' && frac == '00') return null;
  return '$whole.$frac';
}

/// "2026-10-08T17:05:00Z" -> "08-Oct-2026, 10:35 PM" in the phone's time: when money changed hands.
String formatStamp(String? iso) {
  if (iso == null || iso.isEmpty) return '';
  final d = DateTime.tryParse(iso)?.toLocal();
  if (d == null) return iso;
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  final hour = d.hour % 12 == 0 ? 12 : d.hour % 12;
  return '${d.day.toString().padLeft(2, '0')}-${months[d.month - 1]}-${d.year}, '
      '${hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')} ${d.hour < 12 ? 'AM' : 'PM'}';
}

/// "2026-10-07T15:55:35Z" -> "07 Oct 2026" in local time.
String formatDate(String? iso, {bool withTime = false}) {
  if (iso == null || iso.isEmpty) return '';
  final d = DateTime.tryParse(iso)?.toLocal();
  if (d == null) return iso;
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  final date = '${d.day.toString().padLeft(2, '0')} ${months[d.month - 1]} ${d.year}';
  if (!withTime) return date;
  return '$date, ${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';
}
