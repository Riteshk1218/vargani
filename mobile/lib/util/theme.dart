import 'package:flutter/material.dart';

/// App colors. The names match the API's `theme_color` values and the website's palettes.
const themeSeeds = <String, Color>{
  'orange': Color(0xFFE65100),
  'red': Color(0xFFD32F2F),
  'maroon': Color(0xFF80232C),
  'pink': Color(0xFFD81B60),
  'purple': Color(0xFF7E22CE),
  'indigo': Color(0xFF4338CA),
  'blue': Color(0xFF1D4ED8),
  'teal': Color(0xFF0F766E),
  'green': Color(0xFF15803D),
};

const defaultThemeColor = 'orange';

Color seedFor(String? name) => themeSeeds[name] ?? themeSeeds[defaultThemeColor]!;

/// The whole app's look, built from one color.
ThemeData buildTheme(String? colorName, Brightness brightness) {
  final scheme = ColorScheme.fromSeed(seedColor: seedFor(colorName), brightness: brightness);
  final rounded = RoundedRectangleBorder(borderRadius: BorderRadius.circular(14));
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: brightness == Brightness.light ? Color.alphaBlend(scheme.primary.withValues(alpha: 0.03), Colors.white) : null,
    appBarTheme: AppBarTheme(
      backgroundColor: scheme.primaryContainer,
      foregroundColor: scheme.onPrimaryContainer,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 2,
      titleTextStyle: TextStyle(color: scheme.onPrimaryContainer, fontSize: 18, fontWeight: FontWeight.w600),
    ),
    cardTheme: CardThemeData(
      elevation: 0,
      shape: rounded.copyWith(side: BorderSide(color: scheme.outlineVariant.withValues(alpha: 0.6))),
      clipBehavior: Clip.antiAlias,
      color: scheme.surfaceContainerLowest,
    ),
    navigationBarTheme: NavigationBarThemeData(
      indicatorColor: scheme.primaryContainer,
      backgroundColor: scheme.surface,
      surfaceTintColor: scheme.primary,
      elevation: 3,
      labelTextStyle: WidgetStateProperty.resolveWith(
        (states) => TextStyle(
          fontSize: 12,
          fontWeight: states.contains(WidgetState.selected) ? FontWeight.w700 : FontWeight.w500,
          color: states.contains(WidgetState.selected) ? scheme.primary : scheme.onSurfaceVariant,
        ),
      ),
    ),
    floatingActionButtonTheme: FloatingActionButtonThemeData(
      backgroundColor: scheme.primary,
      foregroundColor: scheme.onPrimary,
      elevation: 4,
      shape: rounded,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size(64, 48),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        textStyle: const TextStyle(fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(64, 48),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: scheme.surfaceContainerLowest,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: scheme.outlineVariant),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: scheme.primary, width: 2),
      ),
    ),
    chipTheme: ChipThemeData(shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
    listTileTheme: ListTileThemeData(iconColor: scheme.primary),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    ),
    pageTransitionsTheme: const PageTransitionsTheme(
      builders: {TargetPlatform.android: FadeForwardsPageTransitionsBuilder()},
    ),
  );
}

/// Round color swatches. [orgColor] adds an "organization color" choice (the empty value).
class ThemeSwatches extends StatelessWidget {
  const ThemeSwatches({
    super.key,
    required this.value,
    required this.onChanged,
    required this.label,
    this.orgColor,
    this.orgLabel,
  });

  final String value;
  final ValueChanged<String> onChanged;
  final String Function(String color) label;
  final String? orgColor;
  final String? orgLabel;

  @override
  Widget build(BuildContext context) {
    Widget swatch(String key, String name, Color color, {IconData? icon}) {
      final selected = value == key;
      return Tooltip(
        message: name,
        child: InkWell(
          key: Key('theme-${key.isEmpty ? 'org' : key}'),
          customBorder: const CircleBorder(),
          onTap: () => onChanged(key),
          child: Semantics(
            selected: selected,
            label: name,
            child: Padding(
              padding: const EdgeInsets.all(4),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [Color.lerp(color, Colors.white, 0.3)!, color],
                    ),
                    border: Border.all(
                      color: selected ? Theme.of(context).colorScheme.onSurface : Colors.transparent,
                      width: 2.5,
                    ),
                    boxShadow: [BoxShadow(color: color.withValues(alpha: 0.35), blurRadius: selected ? 10 : 4)],
                  ),
                  child: selected
                      ? const Icon(Icons.check, color: Colors.white)
                      : (icon == null ? null : Icon(icon, color: Colors.white, size: 20)),
                ),
                const SizedBox(height: 4),
                SizedBox(
                  width: 64,
                  child: Text(
                    name,
                    textAlign: TextAlign.center,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                ),
              ]),
            ),
          ),
        ),
      );
    }

    return Wrap(spacing: 2, runSpacing: 6, children: [
      if (orgColor != null) swatch('', orgLabel ?? '', seedFor(orgColor), icon: Icons.apartment),
      for (final e in themeSeeds.entries) swatch(e.key, label(e.key), e.value),
    ]);
  }
}
