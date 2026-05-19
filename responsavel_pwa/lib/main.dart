import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

const supabaseUrl =
    String.fromEnvironment('SUPABASE_URL', defaultValue: '');

const supabaseAnonKey =
    String.fromEnvironment('SUPABASE_ANON_KEY', defaultValue: '');

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  runApp(const BootstrapApp());
}

class BootstrapApp extends StatefulWidget {
  const BootstrapApp({super.key});

  @override
  State<BootstrapApp> createState() => _BootstrapAppState();
}

class _BootstrapAppState extends State<BootstrapApp> {
  bool loading = true;

  String? erro;

  @override
  void initState() {
    super.initState();
    iniciar();
  }

  Future<void> iniciar() async {
    try {
      debugPrint('Inicializando aplicativo...');

      if (supabaseUrl.isEmpty || supabaseAnonKey.isEmpty) {
        throw Exception(
          'SUPABASE_URL ou SUPABASE_ANON_KEY não configuradas.',
        );
      }

      await Supabase.initialize(
        url: supabaseUrl,
        anonKey: supabaseAnonKey,
      ).timeout(const Duration(seconds: 15));

      debugPrint('Supabase conectado.');

      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => const ResponsavelApp(),
          ),
        );
      }
    } catch (e) {
      debugPrint('ERRO INIT => $e');

      setState(() {
        erro = e.toString();
      });
    } finally {
      setState(() {
        loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      home: Scaffold(
        backgroundColor: const Color(0xFFF8FAFC),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: loading
                ? Column(
                    mainAxisSize: MainAxisSize.min,
                    children: const [
                      CircularProgressIndicator(),
                      SizedBox(height: 20),
                      Text(
                        'Conectando ao sistema escolar...',
                        style: TextStyle(fontSize: 16),
                      ),
                    ],
                  )
                : Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(
                        Icons.error_outline,
                        size: 70,
                        color: Colors.red,
                      ),
                      const SizedBox(height: 20),
                      const Text(
                        'Erro ao iniciar o aplicativo',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 20,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        erro ?? 'Erro desconhecido.',
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
          ),
        ),
      ),
    );
  }
}

class ResponsavelApp extends StatelessWidget {
  const ResponsavelApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'EREM PAM Família',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: const Color(0xFF0F766E),
      ),
      home: const ResponsavelCadastroPage(),
    );
  }
}

class ResponsavelCadastroPage extends StatefulWidget {
  const ResponsavelCadastroPage({super.key});

  @override
  State<ResponsavelCadastroPage> createState() =>
      _ResponsavelCadastroPageState();
}

class _ResponsavelCadastroPageState
    extends State<ResponsavelCadastroPage> {
  final inputController = TextEditingController();

  final nomeController = TextEditingController();

  bool buscando = false;

  bool salvando = false;

  String? erro;

  List<Map<String, dynamic>> alunos = [];

  Map<String, dynamic>? alunoSelecionado;

  @override
  void dispose() {
    inputController.dispose();
    nomeController.dispose();
    super.dispose();
  }

  Future<void> buscarAluno(String termo) async {
    if (termo.trim().isEmpty) return;

    setState(() {
      buscando = true;
      erro = null;
      alunos = [];
      alunoSelecionado = null;
    });

    try {
      final supabase = Supabase.instance.client;

      final resultado = await supabase
          .from('alunos')
          .select('id, nome, turma, matricula')
          .filter('nome', 'ilike', '%${termo.trim()}%')
          .order('nome')
          .limit(20)
          .timeout(const Duration(seconds: 10));

      debugPrint('RESULTADO => $resultado');

      setState(() {
        alunos = List<Map<String, dynamic>>.from(resultado);

        if (alunos.isEmpty) {
          erro = 'Nenhum estudante encontrado.';
        }
      });
    } catch (e) {
      debugPrint('ERRO BUSCA => $e');

      setState(() {
        erro = traduzirErro(e);
      });
    } finally {
      setState(() {
        buscando = false;
      });
    }
  }

  Future<void> confirmar() async {
    if (alunoSelecionado == null) return;

    if (nomeController.text.trim().length < 5) {
      setState(() {
        erro = 'Informe o nome completo do responsável.';
      });
      return;
    }

    setState(() {
      salvando = true;
      erro = null;
    });

    try {
      final prefs = await SharedPreferences.getInstance();

      await prefs.setString(
        'aluno_id',
        alunoSelecionado!['id'].toString(),
      );

      await prefs.setString(
        'aluno_nome',
        alunoSelecionado!['nome'] ?? '',
      );

      await prefs.setString(
        'aluno_turma',
        alunoSelecionado!['turma'] ?? '',
      );

      await prefs.setString(
        'responsavel_nome',
        nomeController.text.trim(),
      );

      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => const MuralPage(),
          ),
        );
      }
    } catch (e) {
      setState(() {
        erro = 'Erro ao salvar vínculo.';
      });
    } finally {
      setState(() {
        salvando = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: Column(
              children: [
                Image.asset(
                  'assets/logo_erempam.png',
                  height: 120,
                  errorBuilder: (_, __, ___) => const Icon(
                    Icons.school,
                    size: 80,
                    color: Color(0xFF0F766E),
                  ),
                ),
                const SizedBox(height: 20),
                const Text(
                  'EREM PAM Família',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 28,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Acompanhe comunicados escolares.',
                ),
                const SizedBox(height: 32),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      children: [
                        TextField(
                          controller: inputController,
                          decoration: InputDecoration(
                            labelText: 'Nome do estudante',
                            prefixIcon: const Icon(Icons.search),
                            suffixIcon: buscando
                                ? const Padding(
                                    padding: EdgeInsets.all(12),
                                    child: SizedBox(
                                      width: 20,
                                      height: 20,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    ),
                                  )
                                : IconButton(
                                    icon: const Icon(Icons.send),
                                    onPressed: () {
                                      buscarAluno(
                                        inputController.text,
                                      );
                                    },
                                  ),
                          ),
                          onSubmitted: buscarAluno,
                        ),
                        const SizedBox(height: 20),
                        if (alunos.isNotEmpty)
                          SizedBox(
                            height: 250,
                            child: ListView.builder(
                              itemCount: alunos.length,
                              itemBuilder: (_, index) {
                                final aluno = alunos[index];

                                return ListTile(
                                  title: Text(aluno['nome'] ?? ''),
                                  subtitle: Text(
                                    '${aluno['turma']} • ${aluno['matricula']}',
                                  ),
                                  onTap: () {
                                    setState(() {
                                      alunoSelecionado = aluno;
                                      alunos = [];
                                    });
                                  },
                                );
                              },
                            ),
                          ),
                        if (alunoSelecionado != null) ...[
                          const SizedBox(height: 20),
                          Card(
                            color: Colors.green.shade50,
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                children: [
                                  Text(
                                    alunoSelecionado!['nome'],
                                    style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 18,
                                    ),
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    '${alunoSelecionado!['turma']} • ${alunoSelecionado!['matricula']}',
                                  ),
                                  const SizedBox(height: 20),
                                  TextField(
                                    controller: nomeController,
                                    decoration: const InputDecoration(
                                      labelText:
                                          'Nome do responsável',
                                    ),
                                  ),
                                  const SizedBox(height: 20),
                                  SizedBox(
                                    width: double.infinity,
                                    child: ElevatedButton(
                                      onPressed:
                                          salvando ? null : confirmar,
                                      child: salvando
                                          ? const CircularProgressIndicator()
                                          : const Text(
                                              'Entrar',
                                            ),
                                    ),
                                  )
                                ],
                              ),
                            ),
                          ),
                        ],
                        if (erro != null) ...[
                          const SizedBox(height: 20),
                          Text(
                            erro!,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Colors.red,
                            ),
                          ),
                        ]
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class MuralPage extends StatefulWidget {
  const MuralPage({super.key});

  @override
  State<MuralPage> createState() => _MuralPageState();
}

class _MuralPageState extends State<MuralPage> {
  bool loading = true;

  String? erro;

  String aluno = '';

  String turma = '';

  String responsavel = '';

  String alunoId = '';

  List<Map<String, dynamic>> notificacoes = [];

  @override
  void initState() {
    super.initState();

    carregar();
  }

  Future<void> carregar() async {
    try {
      final prefs = await SharedPreferences.getInstance();

      alunoId = prefs.getString('aluno_id') ?? '';

      aluno = prefs.getString('aluno_nome') ?? '';

      turma = prefs.getString('aluno_turma') ?? '';

      responsavel =
          prefs.getString('responsavel_nome') ?? '';

      final supabase = Supabase.instance.client;

      final resultado = await supabase
          .from('notificacoes_responsaveis')
          .select()
          .eq('aluno_id', alunoId)
          .order('criado_em', ascending: false)
          .timeout(const Duration(seconds: 10));

      notificacoes =
          List<Map<String, dynamic>>.from(resultado);
    } catch (e) {
      erro = traduzirErro(e);
    } finally {
      setState(() {
        loading = false;
      });
    }
  }

  Future<void> sair() async {
    final prefs = await SharedPreferences.getInstance();

    await prefs.clear();

    if (mounted) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => const ResponsavelCadastroPage(),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mural do Estudante'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: sair,
          )
        ],
      ),
      body: loading
          ? const Center(
              child: CircularProgressIndicator(),
            )
          : erro != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text(
                      erro!,
                      textAlign: TextAlign.center,
                    ),
                  ),
                )
              : Column(
                  children: [
                    Container(
                      width: double.infinity,
                      color: Colors.white,
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment:
                            CrossAxisAlignment.start,
                        children: [
                          Text(
                            aluno,
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 18,
                            ),
                          ),
                          Text('Turma: $turma'),
                          Text('Responsável: $responsavel'),
                        ],
                      ),
                    ),
                    Expanded(
                      child: notificacoes.isEmpty
                          ? const Center(
                              child: Text(
                                'Nenhum comunicado disponível.',
                              ),
                            )
                          : ListView.builder(
                              padding: const EdgeInsets.all(16),
                              itemCount: notificacoes.length,
                              itemBuilder: (_, index) {
                                final item =
                                    notificacoes[index];

                                return Card(
                                  child: Padding(
                                    padding:
                                        const EdgeInsets.all(16),
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          item['titulo'] ??
                                              'Comunicado',
                                          style:
                                              const TextStyle(
                                            fontWeight:
                                                FontWeight.bold,
                                            fontSize: 16,
                                          ),
                                        ),
                                        const SizedBox(height: 10),
                                        Text(
                                          item['mensagem'] ?? '',
                                        ),
                                        const SizedBox(height: 12),
                                        Text(
                                          formatarData(
                                            item['criado_em'],
                                          ),
                                          style:
                                              const TextStyle(
                                            fontSize: 12,
                                            color: Colors.grey,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                );
                              },
                            ),
                    ),
                  ],
                ),
    );
  }
}

String formatarData(dynamic value) {
  if (value == null) return '';

  final data =
      DateTime.tryParse(value.toString());

  if (data == null) return '';

  return DateFormat(
    "dd/MM/yyyy 'às' HH:mm",
  ).format(data.toLocal());
}

String traduzirErro(Object erro) {
  final texto = erro.toString().toLowerCase();

  if (texto.contains('failed to fetch') ||
      texto.contains('xmlhttprequest')) {
    return 'Erro de conexão com o servidor escolar.';
  }

  if (texto.contains('jwt')) {
    return 'Erro de autenticação do Supabase.';
  }

  if (texto.contains('timeout')) {
    return 'O servidor demorou para responder.';
  }

  if (texto.contains('relation')) {
    return 'Tabela do banco não encontrada.';
  }

  return 'Erro inesperado: $erro';
}