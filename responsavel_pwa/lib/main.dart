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
        colorScheme: ColorScheme.fromSeed(
          seedColor: seed,
          primary: seed,
          secondary: const Color(0xFF14B8A6),
          surface: const Color(0xFFF8FAFC),
        ),
        useMaterial3: true,
        cardTheme: const CardThemeData(elevation: 0, color: Colors.white),
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

class _ResponsavelCadastroPageState extends State<ResponsavelCadastroPage> {
  final _formKey = GlobalKey<FormState>();
  final _inputController = TextEditingController();
  final _nomeResponsavelController = TextEditingController();

  bool _carregando = false;
  bool _buscandoAlunos = false;
  String? _erroMensagem;

  List<Map<String, dynamic>> _alunosEncontrados = [];
  Map<String, dynamic>? _alunoSelecionado;

  @override
  void dispose() {
    _inputController.dispose();
    _nomeResponsavelController.dispose();
    super.dispose();
  }

  Future<Map<String, dynamic>?> _buscarResponsavelAtivo(String alunoId) async {
    try {
      final res = await Supabase.instance.client
          .from('responsaveis_dispositivos')
          .select()
          .eq('aluno_id', alunoId)
          .eq('ativo', true)
          .maybeSingle();
      return res;
    } catch (_) {
      return null;
    }
  }

  Future<void> _salvarResponsavelDispositivo({
    required String alunoId,
    required String numeroMatricula,
    required String nomeResponsavel,
    required String plataforma,
    String? pushToken,
  }) async {
    await Supabase.instance.client.from('responsaveis_dispositivos').insert({
      'aluno_id': alunoId,
      'numero_matricula': numeroMatricula,
      'nome_responsavel': nomeResponsavel,
      'plataforma': plataforma,
      'push_token': pushToken ?? '',
      'ativo': true,
    });
  }

  Future<void> _pesquisarAlunos(String termo) async {
    if (termo.trim().isEmpty) return;
    setState(() {
      _buscandoAlunos = true;
      _erroMensagem = null;
      _alunosEncontrados = [];
      _alunoSelecionado = null;
    });

    try {
      final supabase = Supabase.instance.client;
      final res = await supabase
          .from('alunos')
          .select('id, nome, turma, matricula')
          .ilike('nome', '%$termo%')
          .order('nome')
          .limit(15);

      setState(() {
        _alunosEncontrados = List<Map<String, dynamic>>.from(res);
        if (_alunosEncontrados.isEmpty) {
          _erroMensagem = 'Nenhum estudante encontrado com esse nome.';
        }
      });
    } catch (e) {
      setState(() => _erroMensagem = _mensagemErroSupabase(e));
    } finally {
      setState(() => _buscandoAlunos = false);
    }
  }

  Future<void> _buscarPorMatricula(String matricula) async {
    if (matricula.trim().isEmpty) return;
    setState(() {
      _buscandoAlunos = true;
      _erroMensagem = null;
      _alunosEncontrados = [];
      _alunoSelecionado = null;
    });

    try {
      final supabase = Supabase.instance.client;
      final res = await supabase
          .from('alunos')
          .select('id, nome, turma, matricula')
          .eq('matricula', matricula.trim())
          .maybeSingle();

      setState(() {
        if (res != null) {
          _alunoSelecionado = Map<String, dynamic>.from(res);
        } else {
          _erroMensagem = 'Matrícula não encontrada no cadastro da escola.';
        }
      });
    } catch (e) {
      setState(() => _erroMensagem = _mensagemErroSupabase(e));
    } finally {
      setState(() => _buscandoAlunos = false);
    }
  }

  Future<void> _concluirVinculo() async {
    if (_alunoSelecionado == null) return;
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _carregando = true;
      _erroMensagem = null;
    });

    try {
      final alunoId = _alunoSelecionado!['id'].toString();
      final matricula = _alunoSelecionado!['matricula']?.toString() ?? '';
      final nomeResponsavel = _nomeResponsavelController.text.trim();

      final jaVinculado = await _buscarResponsavelAtivo(alunoId);

      if (jaVinculado == null) {
        await _salvarResponsavelDispositivo(
          alunoId: alunoId,
          numeroMatricula: matricula,
          nomeResponsavel: nomeResponsavel,
          plataforma: 'web_pwa',
        );
      }

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('aluno_id', alunoId);
      await prefs.setString('aluno_nome', _alunoSelecionado!['nome'] ?? '');
      await prefs.setString('aluno_turma', _alunoSelecionado!['turma'] ?? '');
      await prefs.setString('responsavel_nome', nomeResponsavel);

      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const NoticiasLinhaTempoPage()),
        );
      }
    } catch (e) {
      setState(() => _erroMensagem = 'Falha ao registrar vínculo: $e');
    } finally {
      setState(() => _carregando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Container(
            constraints: const BoxConstraints(maxWidth: 440),
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Icon(Icons.school, size: 64, color: Color(0xFF0F766E)),
                  const SizedBox(height: 16),
                  const Text(
                    'EREM PAM Família',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 26,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF1E293B),
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Acompanhe comunicados e registros do seu estudante.',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 14, color: Colors.black54),
                  ),
                  const SizedBox(height: 32),
                  Card(
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                      side: BorderSide(color: Colors.grey.shade200),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          const Text(
                            'Identifique o Estudante',
                            style: TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 12),
                          TextFormField(
                            controller: _inputController,
                            decoration: InputDecoration(
                              labelText: 'Nome ou Número de Matrícula',
                              prefixIcon: const Icon(Icons.search, size: 20),
                              suffixIcon: _buscandoAlunos
                                  ? const Padding(
                                      padding: EdgeInsets.all(12),
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : null,
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                              ),
                            ),
                            onFieldSubmitted: (val) {
                              final puro = val.trim();
                              if (puro.isEmpty) return;
                              final eNumero = RegExp(r'^\d+$').hasMatch(puro);
                              if (eNumero) {
                                _buscarPorMatricula(puro);
                              } else {
                                _pesquisarAlunos(puro);
                              }
                            },
                          ),
                          const SizedBox(height: 8),
                          const Text(
                            'Digite o nome do aluno ou a matrícula e aperte Enter/Buscar para pesquisar.',
                            style: TextStyle(fontSize: 11, color: Colors.grey),
                          ),
                          if (_alunosEncontrados.isNotEmpty &&
                              _alunoSelecionado == null) ...[
                            const SizedBox(height: 16),
                            const Text(
                              'Selecione o estudante na lista:',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Container(
                              constraints: const BoxConstraints(maxHeight: 180),
                              decoration: BoxDecoration(
                                border: Border.all(color: Colors.grey.shade300),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: ListView.separated(
                                shrinkWrap: true,
                                itemCount: _alunosEncontrados.length,
                                separatorBuilder: (_, __) =>
                                    const Divider(height: 1),
                                itemBuilder: (context, index) {
                                  final al = _alunosEncontrados[index];
                                  return ListTile(
                                    title: Text(
                                      al['nome'] ?? '',
                                      style: const TextStyle(fontSize: 14),
                                    ),
                                    subtitle: Text(
                                      'Turma: ${al['turma'] ?? ''} | Matrícula: ${al['matricula'] ?? ''}',
                                      style: const TextStyle(fontSize: 12),
                                    ),
                                    dense: true,
                                    onTap: () {
                                      setState(() {
                                        _alunoSelecionado = al;
                                        _alunosEncontrados = [];
                                      });
                                    },
                                  );
                                },
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                  if (_alunoSelecionado != null) ...[
                    const SizedBox(height: 16),
                    Card(
                      color: const Color(0xFFF0FDF4),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                        side: const BorderSide(color: Color(0xFFDCFCE7)),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.check_circle,
                                    color: Colors.green),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    _alunoSelecionado!['nome'] ?? '',
                                    style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 15,
                                      color: Color(0xFF166534),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Turma: ${_alunoSelecionado!['turma'] ?? ''}  |  Matrícula: ${_alunoSelecionado!['matricula'] ?? ''}',
                              style: const TextStyle(
                                fontSize: 13,
                                color: Color(0xFF166534),
                              ),
                            ),
                            const SizedBox(height: 16),
                            const Divider(color: Color(0xFFDCFCE7)),
                            const SizedBox(height: 8),
                            TextFormField(
                              controller: _nomeResponsavelController,
                              decoration: InputDecoration(
                                labelText: 'Seu Nome (Mãe, Pai, Responsável)',
                                filled: true,
                                fillColor: Colors.white,
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(8),
                                ),
                              ),
                              validator: (val) {
                                if (val == null || val.trim().isEmpty) {
                                  return 'Por favor, informe seu nome.';
                                }
                                if (val.trim().split(' ').length < 2) {
                                  return 'Informe seu nome completo.';
                                }
                                return null;
                              },
                            ),
                            const SizedBox(height: 16),
                            ElevatedButton(
                              onPressed: _carregando ? null : _concluirVinculo,
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFF0F766E),
                                foregroundColor: Colors.white,
                                padding:
                                    const EdgeInsets.symmetric(vertical: 14),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(8),
                                ),
                              ),
                              child: _carregando
                                  ? const SizedBox(
                                      height: 20,
                                      width: 20,
                                      child: CircularProgressIndicator(
                                        color: Colors.white,
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : const Text(
                                      'Confirmar e Entrar',
                                      style: TextStyle(
                                        fontSize: 15,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                  if (_erroMensagem != null) ...[
                    const SizedBox(height: 16),
                    Text(
                      _erroMensagem!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        color: Colors.red,
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class NoticiasLinhaTempoPage extends StatefulWidget {
  const NoticiasLinhaTempoPage({super.key});

  @override
  State<NoticiasLinhaTempoPage> createState() => _NoticiasLinhaTempoPageState();
}

class _NoticiasLinhaTempoPageState extends State<NoticiasLinhaTempoPage> {
  String _alunoId = '';
  String _alunoNome = '';
  String _alunoTurma = '';
  String _responsavelNome = '';

  bool _carregando = true;
  String? _erro;
  List<Map<String, dynamic>> _notificacoes = [];

  @override
  void initState() {
    super.initState();
    _carregarDadosLocais();
  }

  Future<void> _carregarDadosLocais() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _alunoId = prefs.getString('aluno_id') ?? '';
      _alunoNome = prefs.getString('aluno_nome') ?? '';
      _alunoTurma = prefs.getString('aluno_turma') ?? '';
      _responsavelNome = prefs.getString('responsavel_nome') ?? '';
    });

    if (_alunoId.isEmpty) {
      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const ResponsavelCadastroPage()),
        );
      }
      return;
    }

    _buscarNotificacoes();
  }

  Future<void> _buscarNotificacoes() async {
    setState(() {
      _carregando = true;
      _erro = null;
    });

    try {
      final supabase = Supabase.instance.client;
      final res = await supabase
          .from('notificacoes_responsaveis')
          .select()
          .eq('aluno_id', _alunoId)
          .order('criado_em', ascending: false);

      setState(() {
        _notificacoes = List<Map<String, dynamic>>.from(res);
      });
    } catch (e) {
      setState(() => _erro = _mensagemErroSupabase(e));
    } finally {
      setState(() => _carregando = false);
    }
  }

  Future<void> _sair() async {
    final confirma = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Sair do Aplicativo?'),
        content: const Text(
          'Isso removerá o vínculo com o estudante neste dispositivo. Será necessário identificar a matrícula novamente.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancelar'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Sair', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirma == true) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.clear();
      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const ResponsavelCadastroPage()),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Mural do Estudante',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
        ),
        elevation: 0,
        backgroundColor: Colors.white,
        foregroundColor: const Color(0xFF1E293B),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Atualizar',
            onPressed: _buscarNotificacoes,
          ),
          IconButton(
            icon: const Icon(Icons.logout, color: Colors.grey),
            tooltip: 'Desconectar',
            onPressed: _sair,
          ),
        ],
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            color: Colors.white,
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFF1F5F9),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                children: [
                  const CircleAvatar(
                    backgroundColor: Color(0xFF0F766E),
                    foregroundColor: Colors.white,
                    child: Icon(Icons.person, size: 20),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _alunoNome,
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                            color: Color(0xFF1E293B),
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Turma: $_alunoTurma  |  Resp: $_responsavelNome',
                          style: const TextStyle(
                            fontSize: 12,
                            color: Colors.black54,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          Expanded(
            child: _carregando
                ? const Center(child: CircularProgressIndicator())
                : _erro != null
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.all(24),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                _erro!,
                                textAlign: TextAlign.center,
                                style: const TextStyle(color: Colors.red),
                              ),
                              const SizedBox(height: 12),
                              ElevatedButton(
                                onPressed: _buscarNotificacoes,
                                child: const Text('Tentar Novamente'),
                              ),
                            ],
                          ),
                        ),
                      )
                    : _notificacoes.isEmpty
                        ? const Center(
                            child: Padding(
                              padding: EdgeInsets.all(32),
                              child: Text(
                                'Nenhum comunicado registrado para este estudante até o momento.',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  color: Colors.grey,
                                  fontSize: 14,
                                ),
                              ),
                            ),
                          )
                        : ListView.builder(
                            padding: const EdgeInsets.all(16),
                            itemCount: _notificacoes.length,
                            itemBuilder: (context, index) {
                              final nota = _notificacoes[index];
                              final tipo =
                                  nota['tipo']?.toString() ?? 'comunicado';
                              final titulo =
                                  nota['titulo']?.toString() ?? 'Comunicado';
                              final mensagem =
                                  nota['mensagem']?.toString() ?? '';
                              final dataTexto =
                                  _formatarData(nota['criado_em']);

                              return Card(
                                margin: const EdgeInsets.only(bottom: 12),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                  side:
                                      BorderSide(color: Colors.grey.shade200),
                                ),
                                child: Padding(
                                  padding: const EdgeInsets.all(16),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          Container(
                                            padding: const EdgeInsets.all(6),
                                            decoration: BoxDecoration(
                                              color: _corTipo(tipo)
                                                  .withValues(alpha: 0.1),
                                              shape: BoxShape.circle,
                                            ),
                                            child: Icon(
                                              _iconeTipo(tipo),
                                              color: _corTipo(tipo),
                                              size: 18,
                                            ),
                                          ),
                                          const SizedBox(width: 8),
                                          Expanded(
                                            child: Text(
                                              titulo,
                                              style: const TextStyle(
                                                fontWeight: FontWeight.bold,
                                                fontSize: 15,
                                                color: Color(0xFF1E293B),
                                              ),
                                            ),
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 10),
                                      Text(
                                        mensagem,
                                        style: const TextStyle(
                                          fontSize: 14,
                                          color: Color(0xFF334155),
                                          height: 1.4,
                                        ),
                                      ),
                                      const SizedBox(height: 12),
                                      Align(
                                        alignment: Alignment.bottomRight,
                                        child: Text(
                                          dataTexto,
                                          style: const TextStyle(
                                            fontSize: 11,
                                            color: Colors.grey,
                                          ),
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
    return 'Não consegui conectar ao Supabase. Confira se o app foi publicado com SUPABASE_URL igual à URL do projeto Supabase.';
  }
  if (texto.contains('JWT') || texto.contains('Invalid API key')) {
    return 'Erro de autenticação: SUPABASE_ANON_KEY inválida.';
  }
  if (texto.contains('SocketException') ||
      texto.contains('Failed host lookup') ||
      texto.contains('TypeError: Failed to fetch')) {
    return 'Sem conexão com a internet. Verifique sua rede e tente novamente.';
  }
  return 'Erro na comunicação com a escola: $error';
}