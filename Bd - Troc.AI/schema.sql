-- =====================================================================
-- Troc.ai (Tinder do Conhecimento) - Modelagem relacional (SQLite 3)
-- Responsavel: Pessoa 4 (Daphiny) - Back-end (O Banco)
-- Cobre o ciclo completo das 15 telas da 1a entrega:
--   cadastro/perfil -> skills -> match -> chat -> troca -> sessao
--   -> avaliacao -> reputacao/selos
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. CATALOGO DE HABILIDADES
-- ---------------------------------------------------------------------
CREATE TABLE categorias (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);

CREATE TABLE habilidades (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id)
);

-- ---------------------------------------------------------------------
-- 2. USUARIOS (Telas 01 a 06)
-- ---------------------------------------------------------------------
CREATE TABLE usuarios (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,  -- ex.: #001045
    nome             TEXT NOT NULL CHECK (length(trim(nome)) > 0),
    email            TEXT NOT NULL UNIQUE COLLATE NOCASE
                     CHECK (email LIKE '_%@_%._%'),
    senha_hash       TEXT NOT NULL,                      -- nunca guarda senha pura
    curso            TEXT,
    instituicao      TEXT,
    bio              TEXT,                               -- "Sobre mim"
    foto_url         TEXT,
    cidade           TEXT,
    zona             TEXT,                               -- ex.: Zona Leste
    latitude         REAL CHECK (latitude  BETWEEN  -90 AND  90),
    longitude        REAL CHECK (longitude BETWEEN -180 AND 180),
    nivel_tecnologia TEXT CHECK (nivel_tecnologia IN
                     ('Básico', 'Intermediário', 'Avançado')),
    criado_em        TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Matriz de habilidades: OUT = "O que sei ensinar", IN = "O que quero aprender"
CREATE TABLE usuario_habilidades (
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id)    ON DELETE CASCADE,
    habilidade_id INTEGER NOT NULL REFERENCES habilidades(id),
    tipo          TEXT    NOT NULL CHECK (tipo IN ('OUT', 'IN')),
    PRIMARY KEY (usuario_id, habilidade_id, tipo)
);
CREATE INDEX idx_uh_habilidade ON usuario_habilidades (habilidade_id, tipo);

-- Uma habilidade nao pode ser, ao mesmo tempo, ensinada e desejada
CREATE TRIGGER trg_habilidade_unica_por_tipo
BEFORE INSERT ON usuario_habilidades
BEGIN
    SELECT RAISE(ABORT, 'Habilidade não pode ser oferecida e desejada ao mesmo tempo')
    WHERE EXISTS (SELECT 1 FROM usuario_habilidades
                  WHERE usuario_id = NEW.usuario_id
                    AND habilidade_id = NEW.habilidade_id
                    AND tipo <> NEW.tipo);
END;

-- ---------------------------------------------------------------------
-- 3. MATCHING (Telas 07 a 09)
-- ---------------------------------------------------------------------
-- Cada clique em "Conectar" (♡) ou "Descartar" (✕) no feed
CREATE TABLE interacoes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    de_usuario_id   INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    para_usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    acao            TEXT    NOT NULL CHECK (acao IN ('CONECTAR', 'DESCARTAR')),
    criada_em       TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (de_usuario_id, para_usuario_id),
    CHECK  (de_usuario_id <> para_usuario_id)
);

-- Match = aceitacao mutua. Par sempre ordenado (a < b) para evitar duplicidade.
CREATE TABLE matches (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_a_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    usuario_b_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    indice_afinidade REAL   NOT NULL CHECK (indice_afinidade BETWEEN 0 AND 100),
    criado_em       TEXT    NOT NULL DEFAULT (datetime('now')),
    CHECK  (usuario_a_id < usuario_b_id),
    UNIQUE (usuario_a_id, usuario_b_id)
);

-- Notificacoes automatizadas (afinidade alta, match confirmado)
CREATE TABLE notificacoes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id     INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    ref_usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo           TEXT    NOT NULL CHECK (tipo IN ('MATCH_SUGERIDO', 'MATCH_CONFIRMADO')),
    mensagem       TEXT    NOT NULL,
    lida           INTEGER NOT NULL DEFAULT 0 CHECK (lida IN (0, 1)),
    criada_em      TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (usuario_id, ref_usuario_id, tipo)           -- evita notificar duas vezes
);

-- ---------------------------------------------------------------------
-- 4. CHAT E NEGOCIACAO (Telas 10 e 11)
-- ---------------------------------------------------------------------
CREATE TABLE mensagens (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id     INTEGER NOT NULL REFERENCES matches(id)  ON DELETE CASCADE,
    remetente_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    texto        TEXT    NOT NULL CHECK (length(trim(texto)) > 0),
    enviada_em   TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_mensagens_match ON mensagens (match_id, id);

-- Chat so existe depois do match e so para os dois participantes
CREATE TRIGGER trg_mensagem_somente_match
BEFORE INSERT ON mensagens
BEGIN
    SELECT RAISE(ABORT, 'Chat liberado apenas para os participantes de um match')
    WHERE NOT EXISTS (SELECT 1 FROM matches m
                      WHERE m.id = NEW.match_id
                        AND NEW.remetente_id IN (m.usuario_a_id, m.usuario_b_id));
END;

-- Termos formais da troca: A ensina X a B, B ensina Y a A
CREATE TABLE trocas (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id          INTEGER NOT NULL REFERENCES matches(id)     ON DELETE CASCADE,
    habilidade_a_id   INTEGER NOT NULL REFERENCES habilidades(id),  -- ensinada pelo usuario A
    habilidade_b_id   INTEGER NOT NULL REFERENCES habilidades(id),  -- ensinada pelo usuario B
    objetivo          TEXT,
    criada_em         TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Cada lado so pode ensinar o que declarou em Skills Out
CREATE TRIGGER trg_troca_habilidades_validas
BEFORE INSERT ON trocas
BEGIN
    SELECT RAISE(ABORT, 'Habilidade do usuário A não consta em seus Skills Out')
    WHERE NOT EXISTS (
        SELECT 1 FROM matches m
        JOIN usuario_habilidades uh ON uh.usuario_id = m.usuario_a_id
             AND uh.tipo = 'OUT' AND uh.habilidade_id = NEW.habilidade_a_id
        WHERE m.id = NEW.match_id);
    SELECT RAISE(ABORT, 'Habilidade do usuário B não consta em seus Skills Out')
    WHERE NOT EXISTS (
        SELECT 1 FROM matches m
        JOIN usuario_habilidades uh ON uh.usuario_id = m.usuario_b_id
             AND uh.tipo = 'OUT' AND uh.habilidade_id = NEW.habilidade_b_id
        WHERE m.id = NEW.match_id);
END;

-- ---------------------------------------------------------------------
-- 5. SESSOES, AVALIACAO E REPUTACAO (Telas 12 a 15)
-- ---------------------------------------------------------------------
CREATE TABLE sessoes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    troca_id      INTEGER NOT NULL REFERENCES trocas(id) ON DELETE CASCADE,
    data_hora     TEXT    NOT NULL,                      -- 'AAAA-MM-DD HH:MM'
    modalidade    TEXT    NOT NULL CHECK (modalidade IN ('ONLINE', 'PRESENCIAL')),
    local_ou_link TEXT,
    status        TEXT    NOT NULL DEFAULT 'AGENDADA'
                  CHECK (status IN ('AGENDADA', 'CONCLUIDA', 'CANCELADA')),
    concluida_em  TEXT
);

CREATE TABLE avaliacoes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sessao_id    INTEGER NOT NULL REFERENCES sessoes(id)  ON DELETE CASCADE,
    avaliador_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    avaliado_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    nota         INTEGER NOT NULL CHECK (nota BETWEEN 1 AND 5),
    comentario   TEXT,
    criada_em    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (sessao_id, avaliador_id),                    -- 1 avaliacao por pessoa/sessao
    CHECK  (avaliador_id <> avaliado_id)
);

-- So avalia depois da sessao concluida, e somente quem participou
CREATE TRIGGER trg_avaliacao_valida
BEFORE INSERT ON avaliacoes
BEGIN
    SELECT RAISE(ABORT, 'Avaliação só é permitida após a sessão ser concluída')
    WHERE (SELECT status FROM sessoes WHERE id = NEW.sessao_id) <> 'CONCLUIDA';
    SELECT RAISE(ABORT, 'Avaliador e avaliado devem ser participantes do match')
    WHERE NOT EXISTS (
        SELECT 1 FROM sessoes s
        JOIN trocas  t ON t.id = s.troca_id
        JOIN matches m ON m.id = t.match_id
        WHERE s.id = NEW.sessao_id
          AND ((m.usuario_a_id = NEW.avaliador_id AND m.usuario_b_id = NEW.avaliado_id)
            OR (m.usuario_a_id = NEW.avaliado_id  AND m.usuario_b_id = NEW.avaliador_id)));
END;

-- Selos de conquista
CREATE TABLE selos (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT NOT NULL UNIQUE,
    descricao TEXT
);
CREATE TABLE usuario_selos (
    usuario_id   INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    selo_id      INTEGER NOT NULL REFERENCES selos(id),
    conquistado_em TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (usuario_id, selo_id)
);

-- Ao concluir a 1a sessao: registra a data e concede o selo aos dois
CREATE TRIGGER trg_sessao_concluida
AFTER UPDATE OF status ON sessoes
WHEN NEW.status = 'CONCLUIDA' AND OLD.status <> 'CONCLUIDA'
BEGIN
    UPDATE sessoes SET concluida_em = datetime('now') WHERE id = NEW.id;

    INSERT OR IGNORE INTO usuario_selos (usuario_id, selo_id)
    SELECT m.usuario_a_id, (SELECT id FROM selos WHERE nome = 'Primeira Permuta Concluída')
    FROM trocas t JOIN matches m ON m.id = t.match_id WHERE t.id = NEW.troca_id;

    INSERT OR IGNORE INTO usuario_selos (usuario_id, selo_id)
    SELECT m.usuario_b_id, (SELECT id FROM selos WHERE nome = 'Primeira Permuta Concluída')
    FROM trocas t JOIN matches m ON m.id = t.match_id WHERE t.id = NEW.troca_id;
END;

-- ---------------------------------------------------------------------
-- 6. VIEWS DE APOIO (consultadas pela API / logica de match)
-- ---------------------------------------------------------------------

-- Perfil ATIVO no algoritmo: minimo de 3 Skills Out e ao menos 1 Skill In
-- (regra da Tela 04 / Modulo 2 da 1a entrega)
CREATE VIEW v_usuarios_ativos AS
SELECT u.id
FROM usuarios u
WHERE (SELECT COUNT(*) FROM usuario_habilidades WHERE usuario_id = u.id AND tipo = 'OUT') >= 3
  AND (SELECT COUNT(*) FROM usuario_habilidades WHERE usuario_id = u.id AND tipo = 'IN')  >= 1;

-- Quanto da demanda (Skills In) de "demandante" e atendida pela oferta (Skills Out) de "ofertante"
CREATE VIEW v_cobertura AS
SELECT a.id AS demandante_id,
       b.id AS ofertante_id,
       (SELECT COUNT(*) FROM usuario_habilidades i
         WHERE i.usuario_id = a.id AND i.tipo = 'IN') AS total_demanda,
       (SELECT COUNT(*) FROM usuario_habilidades i
          JOIN usuario_habilidades o ON o.habilidade_id = i.habilidade_id
               AND o.tipo = 'OUT' AND o.usuario_id = b.id
         WHERE i.usuario_id = a.id AND i.tipo = 'IN') AS total_atendida
FROM v_usuarios_ativos a
JOIN v_usuarios_ativos b ON a.id <> b.id;

-- Afinidade de skills (0-100) = media da cobertura mutua, por par (a < b)
CREATE VIEW v_afinidade_skills AS
SELECT x.demandante_id AS usuario_a_id,
       x.ofertante_id  AS usuario_b_id,
       ROUND(100.0 * ( (1.0 * x.total_atendida / x.total_demanda)
                     + (1.0 * y.total_atendida / y.total_demanda) ) / 2, 2) AS afinidade_skills
FROM v_cobertura x
JOIN v_cobertura y ON y.demandante_id = x.ofertante_id
                  AND y.ofertante_id  = x.demandante_id
WHERE x.demandante_id < x.ofertante_id
  AND x.total_demanda > 0 AND y.total_demanda > 0;

-- Reputacao publica (Tela 15)
CREATE VIEW v_reputacao AS
SELECT u.id   AS usuario_id,
       u.nome AS nome,
       ROUND(AVG(a.nota), 1) AS nota_media,
       COUNT(a.id)           AS total_avaliacoes,
       (SELECT COUNT(*)
          FROM sessoes s
          JOIN trocas  t ON t.id = s.troca_id
          JOIN matches m ON m.id = t.match_id
         WHERE s.status = 'CONCLUIDA'
           AND u.id IN (m.usuario_a_id, m.usuario_b_id)) AS trocas_concluidas
FROM usuarios u
LEFT JOIN avaliacoes a ON a.avaliado_id = u.id
GROUP BY u.id;
