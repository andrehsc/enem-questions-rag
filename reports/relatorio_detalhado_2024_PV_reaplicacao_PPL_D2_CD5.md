# RELATÓRIO DETALHADO DE EXTRAÇÃO OCR+OLLAMA

## 📄 INFORMAÇÕES DO CADERNO
- **Arquivo:** 2024_PV_reaplicacao_PPL_D2_CD5.pdf
- **Data de Extração:** 17/10/2025 21:18:40
- **Total de Páginas no PDF:** 3
- **Páginas Processadas:** 2 (excluindo página 1 com metadados)
- **Expectativa:** 90-95 questões por caderno ENEM
- **Modo:** Teste detalhado com primeira página ignorada

## 🎯 IDENTIFICAÇÃO DO CADERNO
- **Ano:** 2024
- **Dia:** 2
- **Aplicação:** PV
- **Caderno:** 5

---

## 📄 PÁGINA 2 (do PDF original)
**Dimensões da imagem:** 1185x1628 pixels
**Tamanho do arquivo convertido:** ~5.5 MB

**🖼️ Imagem da página completa:** `extracted_images\pagina_02_completa.png`

### 🔍 DETECÇÃO DE REGIÕES
**Regiões de questão detectadas:** 6

### 📝 QUESTÃO DETECTADA #1

#### 📊 METADADOS DA DETECÇÃO
- **Número identificado:** Q94
- **Página original PDF:** 2
- **Posição (x,y,largura,altura):** (622, 117, 512, 800)
- **Confiança da detecção:** 0.95

**🖼️ Imagem da região extraída:** `extracted_images\pagina_02_questao_Q94_1.png`
- **Dimensões da região:** 512x800 pixels

#### 🔤 EXTRAÇÃO OCR DETALHADA

**🤖 EASYOCR (GPU):**
```
[Confiança: 1.000] UESTÃO 94
[Confiança: 0.686] palavra força é usada em nosso cotidiano com
[Confiança: 0.999] versos
[Confiança: 0.949] significados
[Confiança: 0.905] Em física; essa mesma palavra
[Confiança: 0.782] ssui um significado próprio, diferente daqueles da
[Confiança: 0.933] guagem do nosso dia a dia. As cinco frases seguintes
[Confiança: 0.665] das encontradas em textos literários ou jornalísticos
[Confiança: 0.761] ntêm a palavra força empregada em diversos contextos_
[Confiança: 0.644] 1. "As Forças Armadas estão de prontidão para defender
[Confiança: 0.950] as nossas fronteiras_
[Confiança: 0.935] 2. "Por motivo de força maior; 0 professor não poderá
[Confiança: 0.740] dar aula hoje_
[Confiança: 0.801] 3. "Aforça do pensamento transforma 0 mundo.
[Confiança: 0.842] 4. "Abola bateu na trave e voltou com mais força ainda.
[Confiança: 0.806] 5. "Tudo é atraído para
[Confiança: 0.863] centro da Terra pela força
[Confiança: 1.000] da
[Confiança: 1.000] gravidade
[Confiança: 0.620] abordagem científica do termo força aparece na frase
[Confiança: 1.000] 2
[Confiança: 0.641] 5.
[Confiança: 1.000] UESTÃO 95
[Confiança: 0.786] Problemas no DNA são responsáveis por cerca de
[Confiança: 0.688] etade dos casos de perda de audição na infância
[Confiança: 0.496] n estudo com
[Confiança: 0.932] camundongos mostrou que a injeção de
[Confiança: 0.640] n vírus, geneticamente modificado; no embrião desses
[Confiança: 0.479] limais pode corrigir 0 problema e restaurar parte da audição.
[Confiança: 0.621] Disponível em: www.bbc.com. Acesso em: 11 jul. 2015 (adaptado) .
```
*Caracteres extraídos: 991 | Fragmentos: 30*

#### ✅ TEXTO FINAL SELECIONADO
```
UESTÃO 94 palavra força é usada em nosso cotidiano com significados Em física; essa mesma palavra versos ssui um significado próprio, diferente daqueles da guagem do nosso dia a dia. As cinco frases seguintes das encontradas em textos literários ou jornalísticos ntêm a palavra força empregada em diversos contextos_ 1. "As Forças Armadas estão de prontidão para defender as nossas fronteiras_ 2. "Por motivo de força maior; 0 professor não poderá dar aula hoje_ 3. "Aforça do pensamento transforma 0 mundo. 4. "Abola bateu na trave e voltou com mais força ainda. centro da Terra pela força 5. "Tudo é atraído para gravidade da abordagem científica do termo força aparece na frase 2 5. UESTÃO 95 Problemas no DNA são responsáveis por cerca de etade dos casos de perda de audição na infância camundongos mostrou que a injeção de n vírus, geneticamente modificado; no embrião desses Disponível em: www.bbc.com. Acesso em: 11 jul. 2015 (adaptado) .
```
*Caracteres finais: 945*

#### 🧠 ANÁLISE OLLAMA (IA)
**✅ RESULTADO ESTRUTURADO:**
```json
{
  "question_number": 94,
  "question_text": "Enunciado completo: A palavra força é usada em nosso cotidiano com significados em física; essa mesma palavra tem um significado próprio, diferente daqueles da gama do nosso dia a dia. As cinco frases seguintes foram encontradas em textos literários ou jornalísticos e têm a palavra força empregada em diversos contextos: 1. 'As Forças Armadas estão de prontidão para defender as nossas fronteiras.' 2. 'Por motivo de força maior; o professor não poderá dar aula hoje.' 3. 'Aforça do pensamento transforma o mundo.' 4. 'Abola bateu na trave e voltou com mais força ainda.' 5. 'Centro da Terra pela força' 6. 'Tudo é atraído para gravidade da abordagem científica do termo força aparece na frase 2.",
  "alternatives": {
    "A": "Alternativa A: As Forças Armadas estão de prontidão para defender as nossas fronteiras.",
    "B": "Alternativa B: Por motivo de força maior; o professor não poderá dar aula hoje.",
    "C": "Alternativa C: Aforça do pensamento transforma o mundo.",
    "D": "Alternativa D: Abola bateu na trave e voltou com mais força ainda.",
    "E": "Alternativa E: Centro da Terra pela força."
  },
  "confidence": 0.95
}
```

#### 🎯 QUESTÃO FINAL ESTRUTURADA
- **Número:** Q94
- **Método:** OCR+Ollama
- **Confiança:** 0.95

**📝 Enunciado:**
```
Enunciado completo: A palavra força é usada em nosso cotidiano com significados em física; essa mesma palavra tem um significado próprio, diferente daqueles da gama do nosso dia a dia. As cinco frases seguintes foram encontradas em textos literários ou jornalísticos e têm a palavra força empregada em diversos contextos: 1. 'As Forças Armadas estão de prontidão para defender as nossas fronteiras.' 2. 'Por motivo de força maior; o professor não poderá dar aula hoje.' 3. 'Aforça do pensamento transforma o mundo.' 4. 'Abola bateu na trave e voltou com mais força ainda.' 5. 'Centro da Terra pela força' 6. 'Tudo é atraído para gravidade da abordagem científica do termo força aparece na frase 2.
```

**🔤 Alternativas:**
- **A)** Alternativa A: As Forças Armadas estão de prontidão para defender as nossas fronteiras.
- **B)** Alternativa B: Por motivo de força maior; o professor não poderá dar aula hoje.
- **C)** Alternativa C: Aforça do pensamento transforma o mundo.
- **D)** Alternativa D: Abola bateu na trave e voltou com mais força ainda.
- **E)** Alternativa E: Centro da Terra pela força.

---
### 📝 QUESTÃO DETECTADA #2

#### 📊 METADADOS DA DETECÇÃO
- **Número identificado:** Q91
- **Página original PDF:** 2
- **Posição (x,y,largura,altura):** (30, 187, 512, 441)
- **Confiança da detecção:** 1.00

**🖼️ Imagem da região extraída:** `extracted_images\pagina_02_questao_Q91_2.png`
- **Dimensões da região:** 512x441 pixels

#### 🔤 EXTRAÇÃO OCR DETALHADA

**🤖 EASYOCR (GPU):**
```
[Confiança: 0.835] QUESTÃO 91
[Confiança: 0.758] Em um laboratório; pesquisadores tentavam desenve
[Confiança: 0.946] uma vacina contra um vírus
[Confiança: 0.879] infecta tanto roedores
[Confiança: 0.590] 0 homem. Uma das vacinas foi capaz de imunizar 1009
[Confiança: 0.839] ratos testados, 0 que foi considerado um grande suce
[Confiança: 0.721] Entretanto; quatro semanas após, novos experime
[Confiança: 0.921] com outras cobaias mostraram
[Confiança: 0.626] 40% dos animais
[Confiança: 0.670] sobreviveram a testes para a mesma vacina. Em um tere
[Confiança: 0.696] experimento; três meses depois; apenas 15% das n
[Confiança: 0.689] cobaias sobreviveram aos testes_
[Confiança: 0.610] Qual 0 principal mecanismo envolvido na perda de imunizz
[Confiança: 0.990] das cobaias?
[Confiança: 0.788] Diminuição da carga viral nas cobaias.
[Confiança: 0.756] Supressão do sistema imune das cobaias.
[Confiança: 0.824] Elevada taxa de mutação dos vírus ativos_
[Confiança: 0.876] Perda da memória imunológica das cobaias_
[Confiança: 1.000] que
[Confiança: 1.000] que
```
*Caracteres extraídos: 666 | Fragmentos: 20*

#### ✅ TEXTO FINAL SELECIONADO
```
QUESTÃO 91 Em um laboratório; pesquisadores tentavam desenve uma vacina contra um vírus infecta tanto roedores que 0 homem. Uma das vacinas foi capaz de imunizar 1009 ratos testados, 0 que foi considerado um grande suce Entretanto; quatro semanas após, novos experime com outras cobaias mostraram 40% dos animais que sobreviveram a testes para a mesma vacina. Em um tere experimento; três meses depois; apenas 15% das n cobaias sobreviveram aos testes_ Qual 0 principal mecanismo envolvido na perda de imunizz das cobaias? Diminuição da carga viral nas cobaias. Supressão do sistema imune das cobaias. Elevada taxa de mutação dos vírus ativos_ Perda da memória imunológica das cobaias_
```
*Caracteres finais: 685*

#### 🧠 ANÁLISE OLLAMA (IA)
**✅ RESULTADO ESTRUTURADO:**
```json
{
  "question_number": 91,
  "question_text": "Enunciado completo: Em um laboratório, pesquisadores tentavam desenhar uma vacina contra um vírus que infectava tanto roedores quanto humanos. Uma das vacinas foi capaz de imunizar 1009 ratos testados, mas que foi considerado um grande sucesso. Entretanto; quatro semanas após, novos experimentos com outras cobaias mostraram 40% dos animais que sobreviveram a testes para a mesma vacina. Em um terceiro experimento; três meses depois; apenas 15% das cobaias sobreviveram aos testes. Qual é o principal mecanismo envolvido na perda de imunização das cobaias? Diminuição da carga viral nas cobaias. Supressão do sistema imune das cobaias. Elevada taxa de mutação dos vírus ativos. Perda da memória imunológica das cobaias.",
  "alternatives": {
    "A": "Alternativa A: Diminuição da carga viral nas cobaias",
    "B": "Alternativa B: Supressão do sistema imune das cobaias",
    "C": "Alternativa C: Elevada taxa de mutação dos vírus ativos",
    "D": "Alternativa D: Perda da memória imunológica das cobaias"
  },
  "confidence": 0.95
}
```

#### 🎯 QUESTÃO FINAL ESTRUTURADA
- **Número:** Q91
- **Método:** OCR+Ollama
- **Confiança:** 0.95

**📝 Enunciado:**
```
Enunciado completo: Em um laboratório, pesquisadores tentavam desenhar uma vacina contra um vírus que infectava tanto roedores quanto humanos. Uma das vacinas foi capaz de imunizar 1009 ratos testados, mas que foi considerado um grande sucesso. Entretanto; quatro semanas após, novos experimentos com outras cobaias mostraram 40% dos animais que sobreviveram a testes para a mesma vacina. Em um terceiro experimento; três meses depois; apenas 15% das cobaias sobreviveram aos testes. Qual é o principal mecanismo envolvido na perda de imunização das cobaias? Diminuição da carga viral nas cobaias. Supressão do sistema imune das cobaias. Elevada taxa de mutação dos vírus ativos. Perda da memória imunológica das cobaias.
```

**🔤 Alternativas:**
- **A)** Alternativa A: Diminuição da carga viral nas cobaias
- **B)** Alternativa B: Supressão do sistema imune das cobaias
- **C)** Alternativa C: Elevada taxa de mutação dos vírus ativos
- **D)** Alternativa D: Perda da memória imunológica das cobaias

---
### 📝 QUESTÃO DETECTADA #3

#### 📊 METADADOS DA DETECÇÃO
- **Número identificado:** Q92
- **Página original PDF:** 2
- **Posição (x,y,largura,altura):** (30, 643, 512, 800)
- **Confiança da detecção:** 0.80

**🖼️ Imagem da região extraída:** `extracted_images\pagina_02_questao_Q92_3.png`
- **Dimensões da região:** 512x800 pixels

#### 🔤 EXTRAÇÃO OCR DETALHADA

**🤖 EASYOCR (GPU):**
```
[Confiança: 0.167] IiuucI
[Confiança: 0.480] ga
[Confiança: 0.302] Uc
[Confiança: 0.027] GnC
[Confiança: 0.343] l
[Confiança: 0.075] IUiU
[Confiança: 0.066] ai2
[Confiança: 0.994] QUESTÃO 92
[Confiança: 0.755] 0 bioma Pampa corresponde a quase dois terços d
[Confiança: 0.800] Grande do Sul e pouco mais de 2% do Brasil, contendo
[Confiança: 0.637] de 3 mil espécies de plantas. Dentre essas; aproximadam
[Confiança: 0.608] 400 são gramíneas; que são ervas comumente chams
[Confiança: 0.686] de grama ou capim e apresentam polinização pelo v
[Confiança: 0.669] (anemocoria). Esse tipo de polinização é pouco eficiente;
[Confiança: 0.942] encontro entre os grãos de pólen e 0 estigma ocorre ao ac
[Confiança: 0.900] Disponível em: http:Izh.clicrbs.co
[Confiança: 0.674] Acesso em: 15 nov. 2014 (adapt
[Confiança: 0.991] Uma adaptação que também favoreceu 0 sucesso reprod
[Confiança: 0.912] nessas plantas é 0 fato de elas possuírem flores com
[Confiança: 0.739] pétalas atrativas 
[Confiança: 0.994] néctar açucarado
[Confiança: 1.000] odor
[Confiança: 0.736] desagradável.
[Confiança: 0.993] tamanho pronunciado.
[Confiança: 0.893] grãos de pólen numerosos.
[Confiança: 0.999] QUESTÃO 93
[Confiança: 0.719] Segundo especialistas; há uma ligação causal
[Confiança: 0.859] ocupação nos 12 municípios do sistema de capts
[Confiança: 0.838] de água Cantareira;
[Confiança: 0.957] destruição da mata ciliar de
[Confiança: 0.577] 8171 km de rios e 0 esgotamento do sistema: Choveu me
[Confiança: 0.746] no último ano, mas, se a mata nativa ainda estivess
[Confiança: 0.811] os reservatórios poderiam ter mais água
[Confiança: 0.780] de me
[Confiança: 0.545] qualidade. Técnicos propõem 0 plantio de 30 milhõe
[Confiança: 0.963] mudas para recompor a mata ciliar em 34 mil hectares
[Confiança: 0.918] SANT'ANNA, L
[Confiança: 0.617] 0 Estado de S. Paulo; 21 fev. 2015 (adapt
[Confiança: 0.904] Essa ação está diretamente relacionada à prevenção
[Confiança: 0.726] salinização da água.
```
*Caracteres extraídos: 1179 | Fragmentos: 40*

#### ✅ TEXTO FINAL SELECIONADO
```
QUESTÃO 92 0 bioma Pampa corresponde a quase dois terços d Grande do Sul e pouco mais de 2% do Brasil, contendo de 3 mil espécies de plantas. Dentre essas; aproximadam 400 são gramíneas; que são ervas comumente chams de grama ou capim e apresentam polinização pelo v (anemocoria). Esse tipo de polinização é pouco eficiente; encontro entre os grãos de pólen e 0 estigma ocorre ao ac Disponível em: http:Izh.clicrbs.co Acesso em: 15 nov. 2014 (adapt Uma adaptação que também favoreceu 0 sucesso reprod nessas plantas é 0 fato de elas possuírem flores com pétalas atrativas  néctar açucarado desagradável. odor tamanho pronunciado. grãos de pólen numerosos. QUESTÃO 93 Segundo especialistas; há uma ligação causal ocupação nos 12 municípios do sistema de capts de água Cantareira; destruição da mata ciliar de 8171 km de rios e 0 esgotamento do sistema: Choveu me no último ano, mas, se a mata nativa ainda estivess os reservatórios poderiam ter mais água de me qualidade. Técnicos propõem 0 plantio de 30 milhõe mudas para recompor a mata ciliar em 34 mil hectares 0 Estado de S. Paulo; 21 fev. 2015 (adapt SANT'ANNA, L Essa ação está diretamente relacionada à prevenção salinização da água.
```
*Caracteres finais: 1190*

#### 🧠 ANÁLISE OLLAMA (IA)
**✅ RESULTADO ESTRUTURADO:**
```json
{
  "question_number": 91,
  "question_text": "Bioma Pampa corresponde a quase dois terços do Grande do Sul e pouco mais de 2% do Brasil, contendo de 3 mil espécies de plantas. Dentre essas; aproximadamente 400 são gramíneas; que são ervas comumente chamadas de grama ou capim e apresentam polinização pelo vento (anemocoria). Esse tipo de polinização é pouco eficiente, pois encontra entre os grãos de pólen e o estigma ocorre apenas após a disperção. Disponível em: http://izh.clicrbs.co Acesso em: 15 nov. 2014 (adaptada). Uma adaptação que também favoreceu o sucesso reprodutivo nessas plantas é o fato de elas possuírem flores com pétalas atrativas, néctar açucarado desagradável e odor pronunciado. Grãos de pólen numerosos.",
  "alternatives": {
    "A": "Alternativa A...",
    "B": "Alternativa B...",
    "C": "Alternativa C...",
    "D": "Alternativa D...",
    "E": "Alternativa E..."
  },
  "confidence": 0.95
}
```

#### 🎯 QUESTÃO FINAL ESTRUTURADA
- **Número:** Q91
- **Método:** OCR+Ollama
- **Confiança:** 0.95

**📝 Enunciado:**
```
Bioma Pampa corresponde a quase dois terços do Grande do Sul e pouco mais de 2% do Brasil, contendo de 3 mil espécies de plantas. Dentre essas; aproximadamente 400 são gramíneas; que são ervas comumente chamadas de grama ou capim e apresentam polinização pelo vento (anemocoria). Esse tipo de polinização é pouco eficiente, pois encontra entre os grãos de pólen e o estigma ocorre apenas após a disperção. Disponível em: http://izh.clicrbs.co Acesso em: 15 nov. 2014 (adaptada). Uma adaptação que também favoreceu o sucesso reprodutivo nessas plantas é o fato de elas possuírem flores com pétalas atrativas, néctar açucarado desagradável e odor pronunciado. Grãos de pólen numerosos.
```

**🔤 Alternativas:**
- **A)** Alternativa A...
- **B)** Alternativa B...
- **C)** Alternativa C...
- **D)** Alternativa D...
- **E)** Alternativa E...

---
### 📝 QUESTÃO DETECTADA #4

#### 📊 METADADOS DA DETECÇÃO
- **Número identificado:** Q95
- **Página original PDF:** 2
- **Posição (x,y,largura,altura):** (622, 693, 512, 387)
- **Confiança da detecção:** 0.93

**🖼️ Imagem da região extraída:** `extracted_images\pagina_02_questao_Q95_4.png`
- **Dimensões da região:** 512x387 pixels

#### 🔤 EXTRAÇÃO OCR DETALHADA

**🤖 EASYOCR (GPU):**
```
[Confiança: 1.000] UESTÃO 95
[Confiança: 0.786] Problemas no DNA são responsáveis por cerca de
[Confiança: 0.688] etade dos casos de perda de audição na infância
[Confiança: 0.579] n estudo com
[Confiança: 0.932] camundongos mostrou que a injeção de
[Confiança: 0.560] n vírus, geneticamente modificado; no embrião desses
[Confiança: 0.479] limais pode corrigir 0 problema e restaurar parte da audição.
[Confiança: 0.621] Disponível em: www.bbc.com. Acesso em: 11 jul. 2015 (adaptado) .
[Confiança: 0.708] 2 acordo com
[Confiança: 0.923] texto; qual técnica permite a correção
[Confiança: 0.953] rcial do problema?
[Confiança: 0.847] Terapia gênica.
[Confiança: 0.974] Marcação molecular.
[Confiança: 0.993] Clonagem terapêutica.
[Confiança: 0.746] Hibridização genômica.
```
*Caracteres extraídos: 472 | Fragmentos: 15*

#### ✅ TEXTO FINAL SELECIONADO
```
UESTÃO 95 Problemas no DNA são responsáveis por cerca de etade dos casos de perda de audição na infância camundongos mostrou que a injeção de n estudo com n vírus, geneticamente modificado; no embrião desses Disponível em: www.bbc.com. Acesso em: 11 jul. 2015 (adaptado) . texto; qual técnica permite a correção 2 acordo com rcial do problema? Terapia gênica. Marcação molecular. Clonagem terapêutica. Hibridização genômica.
```
*Caracteres finais: 424*

#### 🧠 ANÁLISE OLLAMA (IA)
**✅ RESULTADO ESTRUTURADO:**
```json
{
  "question_number": 95,
  "question_text": "Terapia gênica, Marcação molecular, Clonagem terapêutica e Hibridização genômica são as alternativas corretas para a correção de problemas no DNA responsáveis por perda de audição na infância.",
  "alternatives": {
    "A": "Terapia gênica",
    "B": "Marcação molecular",
    "C": "Clonagem terapêutica",
    "D": "Hibridização genômica"
  },
  "confidence": 0.95
}
```

#### 🎯 QUESTÃO FINAL ESTRUTURADA
- **Número:** Q95
- **Método:** OCR+Ollama
- **Confiança:** 0.95

**📝 Enunciado:**
```
Terapia gênica, Marcação molecular, Clonagem terapêutica e Hibridização genômica são as alternativas corretas para a correção de problemas no DNA responsáveis por perda de audição na infância.
```

**🔤 Alternativas:**
- **A)** Terapia gênica
- **B)** Marcação molecular
- **C)** Clonagem terapêutica
- **D)** Hibridização genômica

---
### 📝 QUESTÃO DETECTADA #5

#### 📊 METADADOS DA DETECÇÃO
- **Número identificado:** Q96
- **Página original PDF:** 2
- **Posição (x,y,largura,altura):** (622, 1095, 512, 503)
- **Confiança da detecção:** 0.68

**🖼️ Imagem da região extraída:** `extracted_images\pagina_02_questao_Q96_5.png`
- **Dimensões da região:** 512x503 pixels

#### 🔤 EXTRAÇÃO OCR DETALHADA

**🤖 EASYOCR (GPU):**
```
[Confiança: 0.726] UESTÃO 96
[Confiança: 0.893] cágado-de-barbelas vive nas águas poluídas do Rio
[Confiança: 0.531] eto, em São José do Rio Preto, interior de São Paulo
[Confiança: 0.496] s animais dessa espécie, usados em estudos de
[Confiança: 0.656] otoxicologia, são atraídos para esses locais por causa
[Confiança: 0.881] acúmulo de matéria orgânica nos pontos de despejo
[Confiança: 0.924] esgoto; ambientes com grande quantidade de metais
[Confiança: 0.920] baixíssimo teor de oxigênio
[Confiança: 0.649] Disponível em: www.unesp.br. Acesso em: 4
[Confiança: 0.818] nov. 2014 (adaptado).
[Confiança: 0.916] esse contexto; do ponto de vista ecológico; esses animais
[Confiança: 0.907] io considerados
[Confiança: 0.998] bioindicadores.
[Confiança: 0.853] biorremediadores-
[Confiança: 1.000] organismos invasores
[Confiança: 1.000] anaeróbios facultativos
[Confiança: 0.836] decompositores adaptados.
[Confiança: 0.825] JA NATUREZA
[Confiança: 0.983] E SUAS TECNOLOGIAS
[Confiança: 0.930] enem2o24
```
*Caracteres extraídos: 605 | Fragmentos: 20*

#### ✅ TEXTO FINAL SELECIONADO
```
UESTÃO 96 cágado-de-barbelas vive nas águas poluídas do Rio eto, em São José do Rio Preto, interior de São Paulo otoxicologia, são atraídos para esses locais por causa acúmulo de matéria orgânica nos pontos de despejo esgoto; ambientes com grande quantidade de metais baixíssimo teor de oxigênio Disponível em: www.unesp.br. Acesso em: 4 nov. 2014 (adaptado). esse contexto; do ponto de vista ecológico; esses animais io considerados bioindicadores. biorremediadores- organismos invasores anaeróbios facultativos decompositores adaptados. enem2o24 JA NATUREZA E SUAS TECNOLOGIAS
```
*Caracteres finais: 578*

#### 🧠 ANÁLISE OLLAMA (IA)
**✅ RESULTADO ESTRUTURADO:**
```json
{
  "question_number": 96,
  "question_text": "Cágado-de-barbelas vive nas águas poluídas do Rio Eto, em São José do Rio Preto, interior de São Paulo. Oxicologia, são atraídos para esses locais por causa acúmulo de matéria orgânica nos pontos de despejo esgoto; ambientes com grande quantidade de metais baixíssimo teor de oxigênio",
  "alternatives": {
    "A": "Alternativa A",
    "B": "Alternativa B",
    "C": "Alternativa C",
    "D": "Alternativa D",
    "E": "Alternativa E"
  },
  "confidence": 0.95
}
```

#### 🎯 QUESTÃO FINAL ESTRUTURADA
- **Número:** Q96
- **Método:** OCR+Ollama
- **Confiança:** 0.95

**📝 Enunciado:**
```
Cágado-de-barbelas vive nas águas poluídas do Rio Eto, em São José do Rio Preto, interior de São Paulo. Oxicologia, são atraídos para esses locais por causa acúmulo de matéria orgânica nos pontos de despejo esgoto; ambientes com grande quantidade de metais baixíssimo teor de oxigênio
```

**🔤 Alternativas:**
- **A)** Alternativa A
- **B)** Alternativa B
- **C)** Alternativa C
- **D)** Alternativa D
- **E)** Alternativa E

---
### 📝 QUESTÃO DETECTADA #6

#### 📊 METADADOS DA DETECÇÃO
- **Número identificado:** Q93
- **Página original PDF:** 2
- **Posição (x,y,largura,altura):** (30, 1101, 512, 497)
- **Confiança da detecção:** 0.86

**🖼️ Imagem da região extraída:** `extracted_images\pagina_02_questao_Q93_6.png`
- **Dimensões da região:** 512x497 pixels

#### 🔤 EXTRAÇÃO OCR DETALHADA

**🤖 EASYOCR (GPU):**
```
[Confiança: 0.189] 9i9u9
[Confiança: 0.273] UC
[Confiança: 0.356] Nuicn
[Confiança: 0.037] Nunciusud
[Confiança: 0.996] QUESTÃO 93
[Confiança: 0.719] Segundo especialistas; há uma ligação causal
[Confiança: 0.702] a ocupação nos 12 municípios do sistema de capta
[Confiança: 0.838] de água Cantareira;
[Confiança: 0.957] destruição da mata ciliar de
[Confiança: 0.881] 8171 km de rios e
[Confiança: 0.324] esgotamento do sistema:. Choveu me
[Confiança: 0.746] no último ano, mas, se a mata nativa ainda estivess
[Confiança: 0.705] os reservatórios poderiam ter mais água
[Confiança: 0.780] de me
[Confiança: 0.812] qualidade. Técnicos propõem 0 plantio de 30 milhõe
[Confiança: 0.909] mudas para recompor a mata ciliar em 34 mil hectares
[Confiança: 0.640] SANT'ANNA, L
[Confiança: 0.617] 0 Estado de S. Paulo; 21 fev. 2015 (adapt
[Confiança: 0.904] Essa ação está diretamente relacionada à prevenção
[Confiança: 0.726] salinização da água.
[Confiança: 0.865] assoreamento do rio
[Confiança: 0.992] compactação do solo.
[Confiança: 0.990] contaminação das margens_
[Confiança: 0.857] eutrofização dos reservatórios.
[Confiança: 0.746] 2" DIA
[Confiança: 0.997] CADERNO 5
[Confiança: 0.999] AMARELO
```
*Caracteres extraídos: 658 | Fragmentos: 27*

#### ✅ TEXTO FINAL SELECIONADO
```
QUESTÃO 93 Segundo especialistas; há uma ligação causal a ocupação nos 12 municípios do sistema de capta de água Cantareira; destruição da mata ciliar de 8171 km de rios e no último ano, mas, se a mata nativa ainda estivess os reservatórios poderiam ter mais água de me qualidade. Técnicos propõem 0 plantio de 30 milhõe mudas para recompor a mata ciliar em 34 mil hectares 0 Estado de S. Paulo; 21 fev. 2015 (adapt SANT'ANNA, L Essa ação está diretamente relacionada à prevenção salinização da água. assoreamento do rio compactação do solo. contaminação das margens_ eutrofização dos reservatórios. CADERNO 5 AMARELO 2" DIA
```
*Caracteres finais: 624*

#### 🧠 ANÁLISE OLLAMA (IA)
**✅ RESULTADO ESTRUTURADO:**
```json
{
  "question_number": 93,
  "question_text": "Segundo especialistas; há uma ligação causal a ocupação nos 12 municípios do sistema de capta de água Cantareira; destruição da mata ciliar de 8171 km de rios e no último ano, mas, se a mata nativa ainda estivesse, os reservatórios poderiam ter mais água de qualidade. Técnicos propõem plantio de 30 milhões de mudas para recompor a mata ciliar em 34 mil hectares no Estado de S. Paulo; 21 fev. 2015 (adapt Sant'Anna, L). Essa ação está diretamente relacionada à prevenção salinização da água, assoreamento do rio, compactação do solo, contaminação das margens e eutrofização dos reservatórios.",
  "alternatives": {
    "A": "Alternativa A...",
    "B": "Alternativa B...",
    "C": "Alternativa C...",
    "D": "Alternativa D...",
    "E": "Alternativa E..."
  },
  "confidence": 0.95
}
```

#### 🎯 QUESTÃO FINAL ESTRUTURADA
- **Número:** Q93
- **Método:** OCR+Ollama
- **Confiança:** 0.95

**📝 Enunciado:**
```
Segundo especialistas; há uma ligação causal a ocupação nos 12 municípios do sistema de capta de água Cantareira; destruição da mata ciliar de 8171 km de rios e no último ano, mas, se a mata nativa ainda estivesse, os reservatórios poderiam ter mais água de qualidade. Técnicos propõem plantio de 30 milhões de mudas para recompor a mata ciliar em 34 mil hectares no Estado de S. Paulo; 21 fev. 2015 (adapt Sant'Anna, L). Essa ação está diretamente relacionada à prevenção salinização da água, assoreamento do rio, compactação do solo, contaminação das margens e eutrofização dos reservatórios.
```

**🔤 Alternativas:**
- **A)** Alternativa A...
- **B)** Alternativa B...
- **C)** Alternativa C...
- **D)** Alternativa D...
- **E)** Alternativa E...

---
---

## 📄 PÁGINA 3 (do PDF original)
**Dimensões da imagem:** 1185x1628 pixels
**Tamanho do arquivo convertido:** ~5.5 MB

**🖼️ Imagem da página completa:** `extracted_images\pagina_03_completa.png`

### 🔍 DETECÇÃO DE REGIÕES
**Regiões de questão detectadas:** 3

### 📝 QUESTÃO DETECTADA #1

#### 📊 METADADOS DA DETECÇÃO
- **Número identificado:** Q97
- **Página original PDF:** 3
- **Posição (x,y,largura,altura):** (30, 117, 512, 800)
- **Confiança da detecção:** 1.00

**🖼️ Imagem da região extraída:** `extracted_images\pagina_03_questao_Q97_1.png`
- **Dimensões da região:** 512x800 pixels

#### 🔤 EXTRAÇÃO OCR DETALHADA

**🤖 EASYOCR (GPU):**
```
[Confiança: 0.920] QUESTÃO 97
[Confiança: 0.842] uso excessivo de embalagens plásticas ocasic
[Confiança: 0.786] um aumento
[Confiança: 0.938] na quantidade de resíduos plást
[Confiança: 0.767] descartados no meio ambiente. Para minimizar 0 imp
[Confiança: 0.632] causado pelo acúmulo desses resíduos, pode-se empr
[Confiança: 0.717] alguns procedimentos:
[Confiança: 1.000] Incineração;
[Confiança: 0.993] Reciclagem;
[Confiança: 0.661] III
[Confiança: 1.000] Acondicionamento em aterros sanitários;
[Confiança: 0.997] IV
[Confiança: 0.821] Substituição por plásticos biodegradáveis;
[Confiança: 0.990] Substituição por plásticos oxibiodegradáveis _
[Confiança: 0.915] Do ponto de vista ambiental,
[Confiança: 0.990] procedimento adequ
[Confiança: 0.676] para solucionar 0 problema de acúmulo desses materi
[Confiança: 0.726] incinerar; pois isso reduz a quantidade de resíduos sól
[Confiança: 0.790] os gases liberados nesse processo não são poluer
[Confiança: 0.882] reciclar; pois 0 plástico descartado é utilizado pa
[Confiança: 0.741] produção de novos objetos, e isso evita a síntes
[Confiança: 0.959] maior quantidade de matéria-prima.
[Confiança: 0.699] utilizar plásticos biodegradáveis, uma
[Confiança: 0.721] vez qL
[Confiança: 0.850] matéria-prima é de fonte renovável e a produção de
[Confiança: 0.732] materiais é simples e de baixo custo.
[Confiança: 0.858] dispensar em aterros sanitários; já que esses locais
[Confiança: 0.992] dimensionados para receber uma grande quantidad
[Confiança: 0.805] resíduos e sua capacidade não se esgota rapidame
[Confiança: 0.657] substituir por plásticos oxibiodegradáveis;
[Confiança: 1.000] visto
[Confiança: 0.832] ao serem descartados; são rapidamente assimilados
```
*Caracteres extraídos: 1079 | Fragmentos: 32*

#### ✅ TEXTO FINAL SELECIONADO
```
QUESTÃO 97 uso excessivo de embalagens plásticas ocasic na quantidade de resíduos plást um aumento descartados no meio ambiente. Para minimizar 0 imp causado pelo acúmulo desses resíduos, pode-se empr alguns procedimentos: Incineração; Reciclagem; Acondicionamento em aterros sanitários; III Substituição por plásticos biodegradáveis; IV Substituição por plásticos oxibiodegradáveis _ procedimento adequ Do ponto de vista ambiental, para solucionar 0 problema de acúmulo desses materi incinerar; pois isso reduz a quantidade de resíduos sól os gases liberados nesse processo não são poluer reciclar; pois 0 plástico descartado é utilizado pa produção de novos objetos, e isso evita a síntes maior quantidade de matéria-prima. utilizar plásticos biodegradáveis, uma vez qL matéria-prima é de fonte renovável e a produção de materiais é simples e de baixo custo. dispensar em aterros sanitários; já que esses locais dimensionados para receber uma grande quantidad resíduos e sua capacidade não se esgota rapidame substituir por plásticos oxibiodegradáveis; visto ao serem descartados; são rapidamente assimilados
```
*Caracteres finais: 1110*

#### 🧠 ANÁLISE OLLAMA (IA)
**❌ OLLAMA:** Falhou na estruturação (possível erro de formato JSON)

#### ❌ QUESTÃO NÃO ESTRUTURADA
Não foi possível estruturar esta questão (possível texto incompleto ou sem alternativas)

---
### 📝 QUESTÃO DETECTADA #2

#### 📊 METADADOS DA DETECÇÃO
- **Número identificado:** Q99
- **Página original PDF:** 3
- **Posição (x,y,largura,altura):** (622, 119, 512, 800)
- **Confiança da detecção:** 0.69

**🖼️ Imagem da região extraída:** `extracted_images\pagina_03_questao_Q99_2.png`
- **Dimensões da região:** 512x800 pixels

#### 🔤 EXTRAÇÃO OCR DETALHADA

**🤖 EASYOCR (GPU):**
```
[Confiança: 1.000] UESTÃO 99
[Confiança: 0.768] Ao respirarmos; falarmos, tossirmos ou espirrarmos,
[Confiança: 0.951] eramos gotículas e aerossóis. Se estamos com alguma
[Confiança: 0.791] fecção respiratória viral, vírus estarão contidos ali.
[Confiança: 0.937] stima-se que uma pessoa com covid-19 falando alto por
[Confiança: 0.457] minuto pode gerar mais de 1 000 partículas de aerossóis;
[Confiança: 0.843] que poderia levar à liberação de mais de 100000 partículas
[Confiança: 0.812] rais de SARS-CoV-2
[Confiança: 0.898] 0 uso de máscaras pela população
[Confiança: 0.952] de auxiliar na redução da transmissão desse vírus
[Confiança: 0.923] nforme representado na figura.
[Confiança: 0.973] Pessoa infectada
[Confiança: 0.997] Pessoas
[Confiança: 1.000] assintomática
[Confiança: 0.842] saudáveis
[Confiança: 1.000] Exposição
[Confiança: 1.000] máxima
[Confiança: 1.000] Exposição
[Confiança: 0.757] mínima
```
*Caracteres extraídos: 536 | Fragmentos: 19*

#### ✅ TEXTO FINAL SELECIONADO
```
UESTÃO 99 Ao respirarmos; falarmos, tossirmos ou espirrarmos, eramos gotículas e aerossóis. Se estamos com alguma fecção respiratória viral, vírus estarão contidos ali. stima-se que uma pessoa com covid-19 falando alto por que poderia levar à liberação de mais de 100000 partículas rais de SARS-CoV-2 0 uso de máscaras pela população de auxiliar na redução da transmissão desse vírus nforme representado na figura. Pessoa infectada Pessoas assintomática saudáveis Exposição máxima Exposição mínima
```
*Caracteres finais: 497*

#### 🧠 ANÁLISE OLLAMA (IA)
**✅ RESULTADO ESTRUTURADO:**
```json
{
  "question_number": 99,
  "question_text": "Enunciado completo: Ao respirarmos, falarmos, tossirmos ou espirrarmos, eramos gotículas e aerossóis. Se estamos com alguma fecção respiratória viral, vírus estarão contidos ali. Stima-se que uma pessoa com covid-19 falando alto poderia levar à liberação de mais de 100.000 partículas raios de SARS-CoV-2.",
  "alternatives": {
    "A": "Alternativa A: Uma pessoa infectada sem sintomas pode contaminar outras pessoas",
    "B": "Alternativa B: O uso de máscaras pela população auxilia na redução da transmissão do vírus.",
    "C": "Alternativa C: Pessoas assintomáticas são mais propensas a transmitir o vírus",
    "D": "Alternativa D: A exposição máxima ao vírus é mais importante que a mínima",
    "E": "Alternativa E: O uso de máscaras não é necessário para pessoas saudáveis"
  },
  "confidence": 0.95
}
```

#### 🎯 QUESTÃO FINAL ESTRUTURADA
- **Número:** Q99
- **Método:** OCR+Ollama
- **Confiança:** 0.95

**📝 Enunciado:**
```
Enunciado completo: Ao respirarmos, falarmos, tossirmos ou espirrarmos, eramos gotículas e aerossóis. Se estamos com alguma fecção respiratória viral, vírus estarão contidos ali. Stima-se que uma pessoa com covid-19 falando alto poderia levar à liberação de mais de 100.000 partículas raios de SARS-CoV-2.
```

**🔤 Alternativas:**
- **A)** Alternativa A: Uma pessoa infectada sem sintomas pode contaminar outras pessoas
- **B)** Alternativa B: O uso de máscaras pela população auxilia na redução da transmissão do vírus.
- **C)** Alternativa C: Pessoas assintomáticas são mais propensas a transmitir o vírus
- **D)** Alternativa D: A exposição máxima ao vírus é mais importante que a mínima
- **E)** Alternativa E: O uso de máscaras não é necessário para pessoas saudáveis

---
### 📝 QUESTÃO DETECTADA #3

#### 📊 METADADOS DA DETECÇÃO
- **Número identificado:** Q98
- **Página original PDF:** 3
- **Posição (x,y,largura,altura):** (30, 947, 512, 651)
- **Confiança da detecção:** 0.81

**🖼️ Imagem da região extraída:** `extracted_images\pagina_03_questao_Q98_3.png`
- **Dimensões da região:** 512x651 pixels

#### 🔤 EXTRAÇÃO OCR DETALHADA

**🤖 EASYOCR (GPU):**
```
[Confiança: 0.652] QUESTÃO 98
[Confiança: 0.883] As Ihamas que vivem nas montanhas dos Ar
[Confiança: 0.793] da América do Sul têm hemoglobinas geneticame
[Confiança: 0.931] diferenciadas de outros mamíferos que vivem ao
[Confiança: 0.877] do mar; por exemplo. Essa diferenciação trata-se de
[Confiança: 0.825] adaptação à sua sobrevivência em altitudes elevadas
[Confiança: 0.814] ar é rarefeito.
[Confiança: 0.545] SCHMIDT-NIELSEN, K. Fisiologia animal: adapu
[Confiança: 0.652] ao meio ambiente. São Paulo: Santos
[Confiança: 0.566] A adaptação desses animais em relação ao seu ambi
[Confiança: 0.921] confere maior
[Confiança: 0.975] afinidade pelo
[Confiança: 0.873] 2' maximizando a captação desse
[Confiança: 0.593] capacidade de tamponamento; evitando alteraçõe
[Confiança: 0.995] pH no sangue
[Confiança: 0.785] afinidade pelo CO2' facilitando seu transporte
[Confiança: 0.816] eliminação nos pulmões
[Confiança: 0.821] 0 velocidade no transporte de gases, aumentanc
[Confiança: 0.946] eficiência de troca gasosa.
[Confiança: 0.835] solubilidade de gases no plasma, melhorando
[Confiança: 1.000] transporte nos tecidos
[Confiança: 0.879] enem2o24
[Confiança: 0.746] 2" DIA
[Confiança: 0.996] CADERNO 5
[Confiança: 0.999] AMARELO
```
*Caracteres extraídos: 738 | Fragmentos: 25*

#### ✅ TEXTO FINAL SELECIONADO
```
QUESTÃO 98 As Ihamas que vivem nas montanhas dos Ar da América do Sul têm hemoglobinas geneticame diferenciadas de outros mamíferos que vivem ao do mar; por exemplo. Essa diferenciação trata-se de adaptação à sua sobrevivência em altitudes elevadas ar é rarefeito. SCHMIDT-NIELSEN, K. Fisiologia animal: adapu ao meio ambiente. São Paulo: Santos A adaptação desses animais em relação ao seu ambi confere maior afinidade pelo 2' maximizando a captação desse capacidade de tamponamento; evitando alteraçõe pH no sangue afinidade pelo CO2' facilitando seu transporte eliminação nos pulmões 0 velocidade no transporte de gases, aumentanc eficiência de troca gasosa. solubilidade de gases no plasma, melhorando transporte nos tecidos enem2o24 CADERNO 5 AMARELO 2" DIA
```
*Caracteres finais: 762*

#### 🧠 ANÁLISE OLLAMA (IA)
**✅ RESULTADO ESTRUTURADO:**
```json
{
  "question_number": 98,
  "question_text": "As ihamas que vivem nas montanhas dos Ara da América do Sul têm hemoglobinas geneticamente diferenciadas de outros mamíferos que vivem ao mar; por exemplo. Essa diferenciação trata-se de adaptação à sua sobrevivência em altitudes elevadas, ar é raro. SCHMIDT-NIELSEN, K. Fisiologia animal: adaptar ao meio ambiente. São Paulo: Santos A adaptação desses animais em relação ao seu ambiente confere maior afinidade pelo 2' maximizando a captação desse capacidade de tamponamento; evitando alterações pH no sangue afinidade pelo CO2' facilitando seu transporte eliminação nos pulmões 0 velocidade no transporte de gases, aumenta a eficiência de troca gasosa. solubilidade de gases no plasma, melhorando transporte nos tecidos",
  "alternatives": {
    "A": "Alternativa A...",
    "B": "Alternativa B...",
    "C": "Alternativa C...",
    "D": "Alternativa D...",
    "E": "Alternativa E..."
  },
  "confidence": 0.95
}
```

#### 🎯 QUESTÃO FINAL ESTRUTURADA
- **Número:** Q98
- **Método:** OCR+Ollama
- **Confiança:** 0.95

**📝 Enunciado:**
```
As ihamas que vivem nas montanhas dos Ara da América do Sul têm hemoglobinas geneticamente diferenciadas de outros mamíferos que vivem ao mar; por exemplo. Essa diferenciação trata-se de adaptação à sua sobrevivência em altitudes elevadas, ar é raro. SCHMIDT-NIELSEN, K. Fisiologia animal: adaptar ao meio ambiente. São Paulo: Santos A adaptação desses animais em relação ao seu ambiente confere maior afinidade pelo 2' maximizando a captação desse capacidade de tamponamento; evitando alterações pH no sangue afinidade pelo CO2' facilitando seu transporte eliminação nos pulmões 0 velocidade no transporte de gases, aumenta a eficiência de troca gasosa. solubilidade de gases no plasma, melhorando transporte nos tecidos
```

**🔤 Alternativas:**
- **A)** Alternativa A...
- **B)** Alternativa B...
- **C)** Alternativa C...
- **D)** Alternativa D...
- **E)** Alternativa E...

---

# 📊 RESUMO FINAL DA EXTRAÇÃO

## 🎯 ESTATÍSTICAS
- **Total de questões extraídas:** 8
- **Páginas processadas:** 2
- **Expectativa ENEM:** 90-95 questões por caderno
- **Taxa de extração:** 8.9% do esperado

## 📋 QUESTÕES IDENTIFICADAS
**Números das questões:** [91, 93, 94, 95, 96, 98, 99]
