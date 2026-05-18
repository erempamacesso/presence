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
  bool _loading = true;
  String? _erro;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    try {
      debugPrint('Inicializando aplicação...');
      debugPrint('SUPABASE_URL => $supabaseUrl');

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
        _erro = e.toString();
      });
    } finally {
      setState(() {
        _loading = false;
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
            child: _loading
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
                        color: Colors.red,
                        size: 70,
                      ),
                      const SizedBox(height: 20),
                      const Text(
                        'Erro ao iniciar o aplicativo',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        _erro ?? 'Erro desconhecido.',
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
  final _inputController = TextEditingController();
  final _nomeController = TextEditingController();

  bool _buscando = false;
  bool _salvando = false;

  String? _erro;

  List<Map<String, dynamic>> _alunos = [];

  Map<String, dynamic>? _selecionado;

  @override
  void dispose() {
    _inputController.dispose();
    _nomeController.dispose();
    super.dispose();
  }

  Future<void> _buscarAluno(String termo) async {
    if (termo.trim().isEmpty) return;

    setState(() {
      _erro = null;
      _buscando = true;
      _alunos = [];
      _selecionado = null;
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

      debugPrint('ALUNOS => $resultado');

      setState(() {
        _alunos = List<Map<String, dynamic>>.from(resultado);

        if (_alunos.isEmpty) {
          _erro = 'Nenhum estudante encontrado.';
        }
      });
    } catch (e) {
      debugPrint('ERRO BUSCA => $e');

      setState(() {
        _erro = traduzirErro(e);
      });
    } finally {
      setState(() {
        _buscando = false;
      });
    }
  }

  Future<void> _confirmar() async {
    if (_selecionado == null) return;

    if (_nomeController.text.trim().length < 5) {
      setState(() {
        _erro = 'Informe o nome completo do responsável.';
      });
      return;
    }

    setState(() {
      _salvando = true;
      _erro = null;
    });

    try {
      final prefs = await SharedPreferences.getInstance();

      await prefs.setString(
        'aluno_id',
        _selecionado!['id'].toString(),
      );

      await prefs.setString(
        'aluno_nome',
        _selecionado!['nome'] ?? '',
      );

      await prefs.setString(
        'aluno_turma',
        _selecionado!['turma'] ?? '',
      );

      await prefs.setString(
        'responsavel_nome',
        _nomeController.text.trim(),
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
        _erro = 'Erro ao salvar vínculo.';
      });
    } finally {
      setState(() {
        _salvando = false;
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
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
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
                          controller: _inputController,
                          decoration: InputDecoration(
                            labelText: 'Nome do estudante',
                            prefixIcon: const Icon(Icons.search),
                            suffixIcon: _buscando
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
                                      _buscarAluno(
                                        _inputController.text,
                                      );
                                    },
                                  ),
                          ),
                          onSubmitted: _buscarAluno,
                        ),
                        const SizedBox(height: 20),
                        if (_alunos.isNotEmpty)
                          SizedBox(
                            height: 250,
                            child: ListView.builder(
                              itemCount: _alunos.length,
                              itemBuilder: (_, index) {
                                final aluno = _alunos[index];

                                return ListTile(
                                  title: Text(aluno['nome'] ?? ''),
                                  subtitle: Text(
                                    '${aluno['turma'] ?? ''} • ${aluno['matricula'] ?? ''}',
                                  ),
                                  onTap: () {
                                    setState(() {
                                      _selecionado = aluno;
                                      _alunos = [];
                                    });
                                  },
                                );
                              },
                            ),
                          ),
                        if (_selecionado != null) ...[
                          const SizedBox(height: 20),
                          Card(
                            color: Colors.green.shade50,
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                children: [
                                  Text(
                                    _selecionado!['nome'] ?? '',
                                    style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 18,
                                    ),
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    '${_selecionado!['turma']} • ${_selecionado!['matricula']}',
                                  ),
                                  const SizedBox(height: 16),
                                  TextField(
                                    controller: _nomeController,
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
                                          _salvando ? null : _confirmar,
                                      child: _salvando
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
                        if (_erro != null) ...[
                          const SizedBox(height: 20),
                          Text(
                            _erro!,
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
  bool _loading = true;

  String? _erro;

  String aluno = '';
  String turma = '';
  String responsavel = '';
  String alunoId = '';

  List<Map<String, dynamic>> notificacoes = [];

  @override
  void initState() {
    super.initState();

    _carregar();
  }

  Future<void> _carregar() async {
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
      _erro = traduzirErro(e);
    } finally {
      setState(() {
        _loading = false;
      });
    }
  }

  Future<void> _sair() async {
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
            onPressed: _sair,
          )
        ],
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(),
            )
          : _erro != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text(
                      _erro!,
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
                          Text(
                            'Turma: $turma',
                          ),
                          Text(
                            'Responsável: $responsavel',
                          ),
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
                                          item['mensagem'] ??
                                              '',
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