import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

const supabaseUrl = String.fromEnvironment('SUPABASE_URL');
const supabaseAnonKey = String.fromEnvironment('SUPABASE_ANON_KEY');

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  if (supabaseUrl.isEmpty || supabaseAnonKey.isEmpty) {
    runApp(const ConfigErrorApp());
    return;
  }

  await Supabase.initialize(url: supabaseUrl, anonKey: supabaseAnonKey);
  runApp(const ResponsavelApp());
}

class ConfigErrorApp extends StatelessWidget {
  const ConfigErrorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: Scaffold(
        body: Center(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Text(
              'Configure SUPABASE_URL e SUPABASE_ANON_KEY usando --dart-define.',
              textAlign: TextAlign.center,
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
    const seed = Color(0xFF0F766E);
    return MaterialApp(
      title: 'EREM PAM Família',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: seed),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF3F4F6),
        cardTheme: const CardThemeData(
          elevation: 0,
          margin: EdgeInsets.zero,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(14)),
          ),
        ),
      ),
      home: const AppGate(),
    );
  }
}

class AppGate extends StatefulWidget {
  const AppGate({super.key});

  @override
  State<AppGate> createState() => _AppGateState();
}

class _AppGateState extends State<AppGate> {
  String? _matricula;
  bool _responsavelCadastrado = false;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _matricula = prefs.getString('matricula_aluno');
      _responsavelCadastrado =
          prefs.getBool('responsavel_cadastrado') ?? false;
      _loading = false;
    });
  }

  Future<void> _saveMatricula(String value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('matricula_aluno', value);
    setState(() {
      _matricula = value;
      _responsavelCadastrado = false;
    });
  }

  Future<void> _onResponsavelCadastrado() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('responsavel_cadastrado', true);
    setState(() => _responsavelCadastrado = true);
  }

  Future<void> _logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('matricula_aluno');
    await prefs.remove('responsavel_cadastrado');
    setState(() {
      _matricula = null;
      _responsavelCadastrado = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (_matricula == null || _matricula!.isEmpty) {
      return LoginPage(onLogin: _saveMatricula);
    }
    if (!_responsavelCadastrado) {
      return ResponsavelCadastroPage(
        matricula: _matricula!,
        onSaved: _onResponsavelCadastrado,
        onLogout: _logout,
      );
    }
    return HomePage(matricula: _matricula!, onLogout: _logout);
  }
}

class ResponsavelCadastroPage extends StatefulWidget {
  const ResponsavelCadastroPage({
    super.key,
    required this.matricula,
    required this.onSaved,
    required this.onLogout,
  });

  final String matricula;
  final Future<void> Function() onSaved;
  final Future<void> Function() onLogout;

  @override
  State<ResponsavelCadastroPage> createState() =>
      _ResponsavelCadastroPageState();
}

class _ResponsavelCadastroPageState extends State<ResponsavelCadastroPage> {
  final _nomeController = TextEditingController();
  final _telefoneController = TextEditingController();
  Map<String, dynamic>? _aluno;
  bool _loading = true;
  bool _saving = false;
  String? _erro;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _nomeController.dispose();
    _telefoneController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final aluno = await _buscarAlunoPorMatricula(widget.matricula);
      if (aluno == null) {
        setState(() => _erro = 'Matrícula não encontrada.');
        return;
      }

      final existente = await _buscarResponsavelAtivo(aluno['id'].toString());
      if (existente != null) {
        _nomeController.text = existente['nome_responsavel']?.toString() ?? '';
        _telefoneController.text = existente['telefone_responsavel']?.toString() ?? '';
      }

      setState(() => _aluno = aluno);
    } catch (error) {
      setState(() => _erro = _mensagemErroSupabase(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _salvar() async {
    final nome = _nomeController.text.trim();
    final telefone = _telefoneController.text.replaceAll(RegExp(r'\D'), '');

    if (nome.length < 3) {
      setState(() => _erro = 'Informe o nome do responsável.');
      return;
    }
    if (telefone.length < 10) {
      setState(() => _erro = 'Informe um telefone válido com DDD.');
      return;
    }
    if (_aluno == null) return;

    setState(() {
      _saving = true;
      _erro = null;
    });

    try {
      await _salvarResponsavelDispositivo(
        aluno: _aluno!,
        nomeResponsavel: nome,
        telefoneResponsavel: telefone,
      );
      await widget.onSaved();
    } catch (error) {
      setState(() => _erro = _mensagemErroSupabase(error));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Cadastro do responsável'),
        actions: [
          IconButton(onPressed: widget.onLogout, icon: const Icon(Icons.logout)),
        ],
      ),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 460),
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        if (_aluno != null) _AlunoHeader(aluno: _aluno!),
                        const SizedBox(height: 16),
                        const _InfoCard(
                          icon: Icons.phone_android,
                          text:
                              'No primeiro acesso, informe um contato do responsável. Esse cadastro será usado pela escola para conferência e futuras notificações.',
                        ),
                        const SizedBox(height: 16),
                        TextField(
                          controller: _nomeController,
                          textCapitalization: TextCapitalization.words,
                          decoration: const InputDecoration(
                            labelText: 'Nome do responsável',
                            border: OutlineInputBorder(),
                            prefixIcon: Icon(Icons.person_outline),
                          ),
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          controller: _telefoneController,
                          keyboardType: TextInputType.phone,
                          decoration: const InputDecoration(
                            labelText: 'Telefone com DDD',
                            hintText: 'Ex: 81999999999',
                            border: OutlineInputBorder(),
                            prefixIcon: Icon(Icons.phone_outlined),
                          ),
                        ),
                        if (_erro != null) ...[
                          const SizedBox(height: 12),
                          Text(
                            _erro!,
                            style: const TextStyle(color: Colors.red),
                          ),
                        ],
                        const SizedBox(height: 16),
                        FilledButton(
                          onPressed: _saving ? null : _salvar,
                          child: _saving
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Text('Salvar e continuar'),
                        ),
                      ],
                    ),
            ),
          ),
        ),
      ),
    );
  }
}

class LoginPage extends StatefulWidget {
  const LoginPage({super.key, required this.onLogin});

  final Future<void> Function(String matricula) onLogin;

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _controller = TextEditingController();
  Timer? _debounce;
  List<Map<String, dynamic>> _resultados = [];
  bool _loading = false;
  bool _buscando = false;
  String? _erro;

  @override
  void dispose() {
    _debounce?.cancel();
    _controller.dispose();
    super.dispose();
  }

  void _onBuscaChanged(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 450), () {
      _buscarPorNome(value);
    });
  }

  Future<void> _buscarPorNome(String value) async {
    final termo = value.trim();
    final apenasNumeros = termo.replaceAll(RegExp(r'\D'), '');

    if (termo.length < 3 || apenasNumeros == termo) {
      if (mounted) setState(() => _resultados = []);
      return;
    }

    setState(() {
      _buscando = true;
      _erro = null;
    });

    try {
      final alunos = await _buscarAlunosPorInicioDoNome(termo);
      if (mounted) setState(() => _resultados = alunos);
    } catch (error) {
      if (mounted) setState(() => _erro = _mensagemErroSupabase(error));
    } finally {
      if (mounted) setState(() => _buscando = false);
    }
  }

  Future<void> _entrar() async {
    final texto = _controller.text.trim();
    final matricula = texto.replaceAll(RegExp(r'\D'), '').trim();
    if (matricula.isEmpty) {
      setState(
        () => _erro = 'Digite a matrícula ou pelo menos 3 letras do nome.',
      );
      return;
    }

    setState(() {
      _loading = true;
      _erro = null;
    });

    try {
      final aluno = await _buscarAlunoPorMatricula(matricula);
      if (aluno == null) {
        setState(() => _erro = 'Matrícula não encontrada.');
        return;
      }
      await widget.onLogin(matricula);
    } catch (error) {
      setState(() => _erro = _mensagemErroSupabase(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _selecionarAluno(Map<String, dynamic> aluno) async {
    final matricula = aluno['numero_matricula']?.toString();
    if (matricula == null || matricula.trim().isEmpty) {
      setState(() => _erro = 'Este estudante está sem matrícula cadastrada.');
      return;
    }
    await widget.onLogin(matricula.trim());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Icon(Icons.school, size: 54, color: Color(0xFF0F766E)),
                  const SizedBox(height: 16),
                  Text(
                    'EREM PAM Família',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Acompanhe comunicados, atrasos e avisos importantes do estudante.',
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 24),
                  TextField(
                    controller: _controller,
                    keyboardType: TextInputType.text,
                    textInputAction: TextInputAction.search,
                    decoration: const InputDecoration(
                      labelText: 'Matrícula ou início do nome',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.search),
                    ),
                    onChanged: _onBuscaChanged,
                    onSubmitted: (_) => _entrar(),
                  ),
                  if (_buscando) ...[
                    const SizedBox(height: 12),
                    const LinearProgressIndicator(),
                  ],
                  if (_resultados.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Card(
                      child: Column(
                        children: _resultados
                            .map(
                              (aluno) => ListTile(
                                leading: const Icon(Icons.person_outline),
                                title: Text(aluno['nome']?.toString() ?? ''),
                                subtitle: Text(
                                  'Turma ${aluno['turma'] ?? '-'} • Matrícula ${aluno['numero_matricula'] ?? '-'}',
                                ),
                                onTap: () => _selecionarAluno(aluno),
                              ),
                            )
                            .toList(),
                      ),
                    ),
                  ],
                  if (_erro != null) ...[
                    const SizedBox(height: 12),
                    Text(_erro!, style: const TextStyle(color: Colors.red)),
                  ],
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: _loading ? null : _entrar,
                    child: _loading
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Entrar'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key, required this.matricula, required this.onLogout});

  final String matricula;
  final Future<void> Function() onLogout;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  Map<String, dynamic>? _aluno;
  List<Map<String, dynamic>> _notificacoes = [];
  bool _loading = true;
  String? _erro;

  @override
  void initState() {
    super.initState();
    _carregar();
  }

  Future<void> _carregar() async {
    setState(() {
      _loading = true;
      _erro = null;
    });

    try {
      final aluno = await _buscarAlunoPorMatricula(widget.matricula);
      if (aluno == null) {
        setState(() => _erro = 'Matrícula não encontrada.');
        return;
      }

      final alunoId = aluno['id'].toString();
      final notificacoes = await Supabase.instance.client
          .from('notificacoes_responsaveis')
          .select()
          .eq('aluno_id', alunoId)
          .order('criado_em', ascending: false)
          .limit(50);

      setState(() {
        _aluno = aluno;
        _notificacoes = List<Map<String, dynamic>>.from(notificacoes);
      });
    } catch (error) {
      setState(() => _erro = _mensagemErroSupabase(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('EREM PAM Família'),
        actions: [
          IconButton(onPressed: _carregar, icon: const Icon(Icons.refresh)),
          IconButton(
            onPressed: widget.onLogout,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _carregar,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (_loading)
                const Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (_erro != null)
                _InfoCard(icon: Icons.error_outline, text: _erro!)
              else ...[
                _AlunoHeader(aluno: _aluno!),
                const SizedBox(height: 16),
                _InstallHint(),
                const SizedBox(height: 16),
                Text(
                  'Comunicados',
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 10),
                if (_notificacoes.isEmpty)
                  const _InfoCard(
                    icon: Icons.notifications_none,
                    text: 'Ainda não há comunicados para este estudante.',
                  )
                else
                  ..._notificacoes.map(
                    (item) => Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: _NotificationCard(item: item),
                    ),
                  ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _AlunoHeader extends StatelessWidget {
  const _AlunoHeader({required this.aluno});

  final Map<String, dynamic> aluno;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            const CircleAvatar(radius: 28, child: Icon(Icons.person)),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    aluno['nome']?.toString() ?? 'Estudante',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text('Turma ${aluno['turma'] ?? '-'}'),
                  Text('Matrícula ${aluno['numero_matricula'] ?? '-'}'),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _InstallHint extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return const Card(
      child: Padding(
        padding: EdgeInsets.all(14),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.install_mobile, color: Color(0xFF0F766E)),
            SizedBox(width: 10),
            Expanded(
              child: Text(
                'Para instalar: abra o menu do navegador e toque em “Adicionar à tela inicial”.',
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _NotificationCard extends StatelessWidget {
  const _NotificationCard({required this.item});

  final Map<String, dynamic> item;

  @override
  Widget build(BuildContext context) {
    final tipo = item['tipo']?.toString() ?? 'comunicado';
    final titulo = item['titulo']?.toString() ?? 'Comunicado';
    final mensagem = item['mensagem']?.toString() ?? '';
    final criadoEm = _formatarData(item['criado_em']);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(_iconeTipo(tipo), color: _corTipo(tipo)),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    titulo,
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(mensagem),
            const SizedBox(height: 10),
            Text(
              criadoEm,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: Colors.grey.shade700),
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          children: [
            Icon(icon, color: const Color(0xFF0F766E)),
            const SizedBox(width: 12),
            Expanded(child: Text(text)),
          ],
        ),
      ),
    );
  }
}

Future<Map<String, dynamic>?> _buscarAlunoPorMatricula(String matricula) async {
  final res = await Supabase.instance.client
      .from('alunos')
      .select()
      .eq('numero_matricula', matricula)
      .maybeSingle();
  return res;
}

Future<List<Map<String, dynamic>>> _buscarAlunosPorInicioDoNome(
  String termo,
) async {
  final res = await Supabase.instance.client
      .from('alunos')
      .select('id, nome, turma, numero_matricula')
      .ilike('nome', '${termo.trim()}%')
      .order('nome')
      .limit(12);
  return List<Map<String, dynamic>>.from(res);
}

String _formatarData(dynamic value) {
  if (value == null) return '';
  final parsed = DateTime.tryParse(value.toString());
  if (parsed == null) return value.toString();
  return DateFormat("dd/MM/yyyy 'às' HH:mm").format(parsed.toLocal());
}

IconData _iconeTipo(String tipo) {
  switch (tipo) {
    case 'atraso':
      return Icons.schedule;
    case 'falta':
      return Icons.event_busy;
    case 'ocorrencia':
      return Icons.report_problem_outlined;
    case 'nota':
      return Icons.assignment_outlined;
    default:
      return Icons.campaign_outlined;
  }
}

Color _corTipo(String tipo) {
  switch (tipo) {
    case 'atraso':
      return Colors.orange.shade700;
    case 'falta':
      return Colors.red.shade700;
    case 'ocorrencia':
      return Colors.deepOrange.shade700;
    case 'nota':
      return Colors.blue.shade700;
    default:
      return const Color(0xFF0F766E);
  }
}

String _mensagemErroSupabase(Object error) {
  final texto = error.toString();
  if (texto.contains('NOT_FOUND') ||
      texto.contains('page could not be found')) {
    return 'Não consegui conectar ao Supabase. Confira se o app foi publicado com SUPABASE_URL igual à URL do projeto Supabase, terminando em .supabase.co.';
  }
  if (texto.contains('permission denied') || texto.contains('RLS')) {
    return 'O Supabase bloqueou a leitura. Confira as políticas RLS das tabelas alunos e notificacoes_responsaveis.';
  }
  return 'Erro ao consultar dados: $error';
}
