-- Carga inicial: catalogo de habilidades e selos (dados de referencia)

INSERT INTO categorias (nome) VALUES
 ('Programação'), ('Web'), ('Design'), ('Hardware e Infraestrutura'),
 ('Produtividade e Dados'), ('Idiomas'), ('Nuvem');

INSERT INTO habilidades (nome, categoria_id) VALUES
 ('Python',                    (SELECT id FROM categorias WHERE nome = 'Programação')),
 ('Lógica de Programação',     (SELECT id FROM categorias WHERE nome = 'Programação')),
 ('Programação Básica',        (SELECT id FROM categorias WHERE nome = 'Programação')),
 ('SQL',                       (SELECT id FROM categorias WHERE nome = 'Programação')),
 ('Git',                       (SELECT id FROM categorias WHERE nome = 'Programação')),
 ('HTML/Web',                  (SELECT id FROM categorias WHERE nome = 'Web')),
 ('Design Gráfico',            (SELECT id FROM categorias WHERE nome = 'Design')),
 ('UI Design',                 (SELECT id FROM categorias WHERE nome = 'Design')),
 ('UX Design',                 (SELECT id FROM categorias WHERE nome = 'Design')),
 ('Figma',                     (SELECT id FROM categorias WHERE nome = 'Design')),
 ('Photoshop',                 (SELECT id FROM categorias WHERE nome = 'Design')),
 ('Illustrator',               (SELECT id FROM categorias WHERE nome = 'Design')),
 ('Identidade Visual',         (SELECT id FROM categorias WHERE nome = 'Design')),
 ('Manutenção de Hardware',    (SELECT id FROM categorias WHERE nome = 'Hardware e Infraestrutura')),
 ('Office',                    (SELECT id FROM categorias WHERE nome = 'Produtividade e Dados')),
 ('Excel Avançado',            (SELECT id FROM categorias WHERE nome = 'Produtividade e Dados')),
 ('Power BI',                  (SELECT id FROM categorias WHERE nome = 'Produtividade e Dados')),
 ('Inglês',                    (SELECT id FROM categorias WHERE nome = 'Idiomas')),
 ('Cloud',                     (SELECT id FROM categorias WHERE nome = 'Nuvem'));

INSERT INTO selos (nome, descricao) VALUES
 ('Primeira Permuta Concluída', 'Concedido após a primeira sessão de troca concluída.');
