import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:responsavel_pwa/main.dart';

void main() {
  testWidgets('shows configuration message without dart defines', (
    tester,
  ) async {
    await tester.pumpWidget(const ConfigErrorApp());

    expect(find.byType(MaterialApp), findsOneWidget);
    expect(find.textContaining('SUPABASE_URL'), findsOneWidget);
  });
}
