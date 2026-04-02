# RELATÓRIO DETALHADO DE EXTRAÇÃO OCR+OLLAMA

## 📄 INFORMAÇÕES DO CADERNO
- **Arquivo:** 2024_PV_reaplicacao_PPL_D2_CD5.pdf
- **Data de Extração:** 17/10/2025 21:36:26
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
- **Posição (x,y,largura,altura):** (612, 112, 552, 556)
- **Confiança da detecção:** 0.95

**🖼️ Imagem da região extraída:** `extracted_images\pagina_02_questao_Q94_1.png`
- **Dimensões da região:** 552x556 pixels

#### 🔤 EXTRAÇÃO OCR DETALHADA

**🔍 TESSERACT OCR:**
```
JUESTÃO 94
A palavra força é usada em nosso cotidiano com
liversos significados. Em física, essa mesma palavra
ossui um significado próprio, diferente daqueles da
nguagem do nosso dia a dia. As cinco frases seguintes,
odas encontradas em textos literários ou jornalísticos,
ontêm a palavra força empregada em diversos contextos.
1. “As Forças Armadas estão de prontidão para defender
as nossas fronteiras.”
2. “Por motivo de força maior, o professor não poderá
dar aula hoje.”
3. “A força do pensamento transforma o mundo.”
4. “A bola bateu na trave e voltou com mais força ainda.”
5. “Tudo é atraído para o centro da Terra pela força
da gravidade.”
t abordagem científica do termo força aparece na frase
D 1.
2.
D3.
nA
```
*Caracteres extraídos: 720*

**🤖 EASYOCR (GPU):**
```
[Confiança: 0.878] JUESTÃO 94
[Confiança: 0.840] A palavra força é usada em nosso cotidiano com
[Confiança: 0.732] liversos significados-
[Confiança: 0.647] Em física, essa mesma palavra
[Confiança: 0.572] ossui um significado próprio, diferente daqueles da
[Confiança: 0.807] nguagem do nosso dia a dia. As cinco frases seguintes
[Confiança: 0.868] odas encontradas em textos literários ou jornalísticos
[Confiança: 0.813] ontêm a palavra força empregada em diversos contextos
[Confiança: 0.730] 1. "As Forças Armadas estão de prontidão para defender
[Confiança: 0.938] as nossas fronteiras_
[Confiança: 0.869] 2. "Por motivo de
[Confiança: 0.870] maior; 0 professor não poderá
[Confiança: 0.724] dar aula hoje_
[Confiança: 0.972] 3. "Aforça do pensamento transforma 0 mundo
[Confiança: 0.516] 4. "Abola bateu na trave e voltou com mais força ainda
[Confiança: 0.684] 5. "Tudo é atraído para
[Confiança: 0.955] 0 centro da Terra pela força
[Confiança: 1.000] da
[Confiança: 1.000] gravidade
[Confiança: 0.871] abordagem científica do termo força aparece na frase
[Confiança: 0.151] 1
[Confiança: 0.966] 3 2
[Confiança: 0.785] 9 3
[Confiança: 0.533] 2
[Confiança: 1.000] força
```
*Caracteres extraídos: 677 | Fragmentos: 25*

#### ✅ TEXTO FINAL SELECIONADO
```
p

JWESTÃO 94 - EznA
ÀA palavra força é usada em nosso cotidiano com É
liversos significados. Em física, essa mesma palavra |
ossui um significado próprio, diferente daqueles da À
nguagem do nosso dia a dia. As cinco frases seguintes, (
odas encontradas em textos literários ou jarnalísticos, :
ontêm a paltavra força empregada em diversos contextos.
1. “As Forças Armadas estão de prontidão para defender j

as nossas fronteiras.” j
2.“Por motivo de força maior, o professor não poderá ;
dar aula hoje.” i

3. “Aforça do pensamento transforma o mundo.” :

4. “A bola bateu na trave e voltou com mais força ainda.” S

5. “Tudo é atraído para o centro da Terra pela força À
da gravidade.” Í

i abordagem científica do termo força aparece na frase s
D3. 1
nAa4 d
```
*Caracteres finais: 760*

#### 🧠 ANÁLISE OLLAMA (IA)
**✅ RESULTADO ESTRUTURADO:**
```json
{
  "question_number": 91,
  "question_text": "Enunciado completo: A palavra força é usada em nosso cotidiano com diversos significados, mas possui um significado próprio na física, diferente daquelas da linguagem do nosso dia a dia. As cinco frases seguintes mostram a palavra força empregada em diferentes contextos literários e jornalísticos.",
  "alternatives": {
    "A": "Alternativa A: A força é uma propriedade física que depende da massa e da aceleração do objeto.",
    "B": "Alternativa B: A força é uma atração ou repulsão entre objetos",
    "C": "Alternativa C: A força é um fenômeno físico que depende da energia cinética de um objeto.",
    "D": "Alternativa D: A força é uma propriedade do espaço que afeta os objetos.",
    "E": "Alternativa E: A força é um conceito matemático que describe a relação entre o momento e a torque."
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
Enunciado completo: A palavra força é usada em nosso cotidiano com diversos significados, mas possui um significado próprio na física, diferente daquelas da linguagem do nosso dia a dia. As cinco frases seguintes mostram a palavra força empregada em diferentes contextos literários e jornalísticos.
```

**🔤 Alternativas:**
- **A)** Alternativa A: A força é uma propriedade física que depende da massa e da aceleração do objeto.
- **B)** Alternativa B: A força é uma atração ou repulsão entre objetos
- **C)** Alternativa C: A força é um fenômeno físico que depende da energia cinética de um objeto.
- **D)** Alternativa D: A força é uma propriedade do espaço que afeta os objetos.
- **E)** Alternativa E: A força é um conceito matemático que describe a relação entre o momento e a torque.

---
### 📝 QUESTÃO DETECTADA #2

#### 📊 METADADOS DA DETECÇÃO
- **Número identificado:** Q91
- **Página original PDF:** 2
- **Posição (x,y,largura,altura):** (20, 182, 552, 436)
- **Confiança da detecção:** 1.00

**🖼️ Imagem da região extraída:** `extracted_images\pagina_02_questao_Q91_2.png`
- **Dimensões da região:** 552x436 pixels

#### 🔤 EXTRAÇÃO OCR DETALHADA

**🔍 TESSERACT OCR:**
```
UCTCAAAS E : A S

QUESTÃO 91
Em um laboratório, pesquisadores tentavam desenvolve

uma vacina contra um vírus que infecta tanto roedores com:
o homem. Uma das vacinas foi capaz de imunizar 100% do:
ratos testados, o que foi considerado um grande sucesso
Entretanto, quatro semanas após, novos experimento:
com outras cobaias mostraram que 40% dos animais nãe
sobreviveram a testes para a mesma vacina. Em um terceir
experimento, três meses depois, apenas 15% das nova:
cobaias sobreviveram aos testes.
Qual o principal mecanismo envolvido na perda de imunizaçãe
das cobaias?
O Diminuição da carga viral nas cobaias.
O Supressão do sistema imune das cobaias.
O Elevada taxa de mutação dos vírus ativos.
FN DaArds ds maemÁria imuinaAalámrisna dse Aqnhkhaiao
```
*Caracteres extraídos: 756*

**🤖 EASYOCR (GPU):**
```
[Confiança: 0.046] Cuc9luC9
[Confiança: 0.040] 4e 91
[Confiança: 0.651] 199
[Confiança: 0.997] QUESTÃO 91
[Confiança: 0.857] Em um laboratório; pesquisadores tentavam desenvolve
[Confiança: 0.925] uma vacina contra um vírus que infecta tanto roedores com
[Confiança: 0.758] 0 homem. Uma das vacinas foi capaz de imunizar 1009 d
[Confiança: 0.604] ratos testados,
[Confiança: 0.600] que foi considerado um grande sucesso
[Confiança: 0.801] Entretanto, quatro semanas após
[Confiança: 0.999] novos experimento
[Confiança: 0.725] com outras cobaias mostraram que 40% dos animais nã
[Confiança: 0.837] sobreviveram a testes para a mesma vacina. Em um terceir
[Confiança: 0.680] experimento; três meses depois, apenas 15% das nova
[Confiança: 0.994] cobaias sobreviveram aos testes
[Confiança: 0.769] Qual 0 principal mecanismo envolvido na perda de imunizaçã
[Confiança: 0.954] das cobaias?
[Confiança: 0.765] Diminuição da carga viral nas cobaias.
[Confiança: 0.755] Supressão do sistema imune das cobaias.
[Confiança: 0.966] Elevada taxa de mutação dos vírus ativos_
[Confiança: 0.008] Gicios
[Confiança: 0.319] Loic
```
*Caracteres extraídos: 675 | Fragmentos: 22*

#### ✅ TEXTO FINAL SELECIONADO
```
AAA V M E ES

QUESTÃO 91 - 2200200000A
Em um laboratório, pesquisadores tentavam desenvolve

uma vacina contra um vírus que infecta tanto roedores com:
o homem. Uma das vacinas foi capaz de imunizar 100% do:
ratos testados, o que foi considerado um grande sucesso
Entretanto, quatro semanas após, novos experimento:
com outras cobaias mostraram que 40% dos animais nãe
sobreviveram a testes para a mesma vacina. Em um terceir:
experimento, três meses depois, apenas 15% das nova:
cobaias sobreviveram aos testes.
Qual o principal mecanismo envolvido na perda de imunizaçãe
das cobaias?
O Diminuição da carga viral nas cobaias.
O Supressão do sistema imune das cobaias.
Q Elevada taxa de mutação dos vírus ativos.
fA Dards dSa mmaAmÁáÁrNraA iIimunsalámina das anhkaias
```
*Caracteres finais: 767*

#### 🧠 ANÁLISE OLLAMA (IA)
**✅ RESULTADO ESTRUTURADO:**
```json
{
  "question_number": 91,
  "question_text": "Qual o principal mecanismo envolvido na perda de imunização das cobaias?\\n\\nDiminuição da carga viral nas cobaias.\\n\\nSupressão do sistema imune das cobaias.\\n\\nElevada taxa de mutação dos vírus ativos.",
  "alternatives": {
    "A": "Diminuição da carga viral nas cobaias.",
    "B": "Supressão do sistema imune das cobaias.",
    "C": "Elevada taxa de mutação dos vírus ativos.",
    "D": "",
    "E": ""
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
Qual o principal mecanismo envolvido na perda de imunização das cobaias?\n\nDiminuição da carga viral nas cobaias.\n\nSupressão do sistema imune das cobaias.\n\nElevada taxa de mutação dos vírus ativos.
```

**🔤 Alternativas:**
- **A)** Diminuição da carga viral nas cobaias.
- **B)** Supressão do sistema imune das cobaias.
- **C)** Elevada taxa de mutação dos vírus ativos.
- **D)** 
- **E)** 

---
### 📝 QUESTÃO DETECTADA #3

#### 📊 METADADOS DA DETECÇÃO
- **Número identificado:** Q92
- **Página original PDF:** 2
- **Posição (x,y,largura,altura):** (20, 638, 552, 438)
- **Confiança da detecção:** 0.80

**🖼️ Imagem da região extraída:** `extracted_images\pagina_02_questao_Q92_3.png`
- **Dimensões da região:** 552x438 pixels

#### 🔤 EXTRAÇÃO OCR DETALHADA

**🔍 TESSERACT OCR:**
```
& Vudarnça da jarnieia ITmunoiogiça dos ariimais (estados
QUESTÃO 92
O bioma Pampa corresponde a quase dois terços do Rit
Grande do Sul e pouco mais de 2% do Brasil, contendo cerc:
de 3 mil espécies de plantas. Dentre essas, aproximadament
400 são gramíneas, que são ervas comumente chamada
de grama ou capim e apresentam polinização pelo vent:
(anemocoria). Esse tipo de polinização é pouco eficiente, pois
encontro entre os grãos de pólen e o estigma ocorre ao acasc
Disponível em: http://zh.clicrbs.com.b
Acesso em: 15 nov. 2014 (adaptado
Uma adaptação que também favoreceu o sucesso reprodutiv.
nessas plantas é o fato de elas possuírem flores com
O pétalas atrativas.
O néctar açucarado.
O odor desagradável.
M tamanhao nreenuinsiadeo
```
*Caracteres extraídos: 740*

**🤖 EASYOCR (GPU):**
```
[Confiança: 0.185] Mviuaança aa Janela Imunoiogica aos animais testaaos
[Confiança: 0.802] QUESTÃO 92
[Confiança: 0.865] 0 bioma Pampa corresponde a quase dois terços do Ric
[Confiança: 0.742] Grande do Sul e pouco mais de 2% do Brasil, contendo cerc
[Confiança: 0.801] de 3 mil espécies de plantas. Dentre essas; aproximadament
[Confiança: 0.806] 400 são gramíneas;
[Confiança: 0.863] são ervas comumente chamada
[Confiança: 0.725] de grama ou capim e apresentam polinização pelo vente
[Confiança: 0.639] (anemocoria). Esse tipo de polinização é pouco eficiente; pois
[Confiança: 0.870] encontro entre os grãos de pólen e 0 estigma ocorre ao acasc
[Confiança: 0.328] Disponível em: http:lIzh.clicrbs.com b
[Confiança: 0.753] Acesso em: 15 nov. 2014 (adaptado
[Confiança: 0.745] Uma adaptação que também favoreceu 0 sucesso reprodutive
[Confiança: 0.794] nessas plantas é 0 fato de elas possuírem flores com
[Confiança: 0.659] pétalas atrativas 
[Confiança: 1.000] néctar açucarado
[Confiança: 0.774] odor desagradável.
[Confiança: 0.678] tamanho
[Confiança: 0.787] nronunciado
[Confiança: 1.000] que
```
*Caracteres extraídos: 701 | Fragmentos: 20*

#### ✅ TEXTO FINAL SELECIONADO
```
1 MUUANÇA a jariçia IMIUTNOIOUIÇA UUS ATNTIAIS IESLAUOS
QUESTÃO 92 - emecc0/070000a00AO,
O bioma Pampa corresponde a quase dois terços do Ri:
Grande do Su! e pouco mais de 2% do Brasil, contendo cerc:
de 3 mil espécies de plantas. Dentre essas, aproximadamentr:
400 são gramíneas, que são ervas comumente chamada
de grama ou capim e apresentam polinização pelo vent:
(anemocoria). Esse tipo de polinização é pouco eficiente, pois :
encontro entre os grãos de pólen e o estigma ocorre ao acasc
Disponível em: http://zh.clicrbs.com.b
Acesso em: 15 nov. 2014 (adaptado
Uma adaptação que também favoreceu o sucesso reprodutiv
nessas plantas é o fato de elas possuírem flores com
O pétalas atrativas.
O néctar açucarado.
O odor desagradável.
M inmanhao nroanimatadao
```
*Caracteres finais: 761*

#### 🧠 ANÁLISE OLLAMA (IA)
**✅ RESULTADO ESTRUTURADO:**
```json
{
  "question_number": 92,
  "question_text": "O bioma Pampa corresponde a quase dois terços do Rio Grande do Sul e pouco mais de 2% do Brasil, contendo cerca de 3 mil espécies de plantas. Dentre essas, aproximadamente 400 são gramíneas, que são ervas comumente chamadas de grama ou capim e apresentam polinização pelo vento (anemocoria). Esse tipo de polinização é pouco eficiente, pois o encontro entre os grãos de pólen e o estigma ocorre ao ascensão. Uma adaptação que também favoreceu o sucesso reprodutivo nessas plantas é o fato de elas possuírem flores com pétalas atrativas, o néctar açucarado e o odor desagradável.",
  "alternatives": {
    "A": "",
    "B": "",
    "C": "",
    "D": "",
    "E": ""
  },
  "confidence": 0.95
}
```

#### 🎯 QUESTÃO FINAL ESTRUTURADA
- **Número:** Q92
- **Método:** OCR+Ollama
- **Confiança:** 0.95

**📝 Enunciado:**
```
O bioma Pampa corresponde a quase dois terços do Rio Grande do Sul e pouco mais de 2% do Brasil, contendo cerca de 3 mil espécies de plantas. Dentre essas, aproximadamente 400 são gramíneas, que são ervas comumente chamadas de grama ou capim e apresentam polinização pelo vento (anemocoria). Esse tipo de polinização é pouco eficiente, pois o encontro entre os grãos de pólen e o estigma ocorre ao ascensão. Uma adaptação que também favoreceu o sucesso reprodutivo nessas plantas é o fato de elas possuírem flores com pétalas atrativas, o néctar açucarado e o odor desagradável.
```

**🔤 Alternativas:**
- **A)** 
- **B)** 
- **C)** 
- **D)** 
- **E)** 

---
### 📝 QUESTÃO DETECTADA #4

#### 📊 METADADOS DA DETECÇÃO
- **Número identificado:** Q95
- **Página original PDF:** 2
- **Posição (x,y,largura,altura):** (612, 688, 552, 400)
- **Confiança da detecção:** 0.93

**🖼️ Imagem da região extraída:** `extracted_images\pagina_02_questao_Q95_4.png`
- **Dimensões da região:** 552x400 pixels

#### 🔤 EXTRAÇÃO OCR DETALHADA

**🔍 TESSERACT OCR:**
```
UESTÃO 95
Problemas no DNA são responsáveis por cerca de

netade dos casos de perda de audição na infância.
Jm estudo com camundongos mostrou que a injeção de
im vírus, geneticamente modificado, no embrião desses
inimais pode corrigir o problema e restaurar parte da audição.

Disponível em: www.bbc.com. Acesso em: 11 jul. 2015 (adaptado).
e acordo com o texto, qual técnica permite a correção
arcial do problema?
) Terapia gênica.
) Marcação molecular.
3 Clonagem terapêutica.
» Hibridização genômica.
3 Saguenciamento aênico
```
*Caracteres extraídos: 528*

**🤖 EASYOCR (GPU):**
```
[Confiança: 0.828] JUESTÃO 95
[Confiança: 0.854] Problemas no DNA são responsáveis por cerca de
[Confiança: 0.851] netade dos casos de perda de audição na infância
[Confiança: 0.844] Jm estudo com camundongos mostrou que a injeção de
[Confiança: 0.800] Im vírus; geneticamente modificado; no embrião desses
[Confiança: 0.667] nimais pode corrigir 0 problema e restaurar parte da audição
[Confiança: 0.725] Disponível em
[Confiança: 0.423] wwwbbc.com. Acesso em: 11 jul. 2015 (adaptado) .
[Confiança: 0.994] e acordo com
[Confiança: 0.778] 0 texto, qual técnica permite a
[Confiança: 1.000] correção
[Confiança: 0.977] arcial do problema?
[Confiança: 0.700] 0 Terapia gênica.
[Confiança: 0.711] 3 Marcação molecular.
[Confiança: 0.998] 9 Clonagem terapêutica
[Confiança: 0.597] 2 Hibridização genômica
[Confiança: 0.489] 3 Seauenciamento aênico
```
*Caracteres extraídos: 504 | Fragmentos: 17*

#### ✅ TEXTO FINAL SELECIONADO
```
WESTÃO 95 - 2200000000A ã
Problemas no DNA são responsáveis por cerca de 1
netade dos casos de perda de audição na infância. 1
Jm estudo com camundongos mostrou que a injeção de !
Im vírus, geneticamente modificado, no embrião desses :
inimais pode corrigir o problema e restaurar parte da audição. ?
Pisponível em: www.bbc.com. Acesso em: 11 jul. 2015 (adaptado). —
Je acordo com o texto, qual técnica permite a correção (
arcial do problema? 1
) Terapia gênica. '
3) Marcação molecular. À
D Clonagem terapêutica. Í
» Hibridização genômica. :
3 Saarenciamentoe aênico P
```
*Caracteres finais: 570*

#### 🧠 ANÁLISE OLLAMA (IA)
**✅ RESULTADO ESTRUTURADO:**
```json
{
  "question_number": 91,
  "question_text": "Qual técnica permite a correção de problemas no DNA e restaurar parte da audição em casos de perda de audição na infância?",
  "alternatives": {
    "A": "Terapia gênica",
    "B": "Marcamento molecular",
    "C": "Clonagem terapêutica",
    "D": "Hibridização genômica",
    "E": "Saarenciamentoe aênico P"
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
Qual técnica permite a correção de problemas no DNA e restaurar parte da audição em casos de perda de audição na infância?
```

**🔤 Alternativas:**
- **A)** Terapia gênica
- **B)** Marcamento molecular
- **C)** Clonagem terapêutica
- **D)** Hibridização genômica
- **E)** Saarenciamentoe aênico P

---
### 📝 QUESTÃO DETECTADA #5

#### 📊 METADADOS DA DETECÇÃO
- **Número identificado:** Q96
- **Página original PDF:** 2
- **Posição (x,y,largura,altura):** (612, 1090, 552, 498)
- **Confiança da detecção:** 0.68

**🖼️ Imagem da região extraída:** `extracted_images\pagina_02_questao_Q96_5.png`
- **Dimensões da região:** 552x498 pixels

#### 🔤 EXTRAÇÃO OCR DETALHADA

**🔍 TESSERACT OCR:**
```
UESTÃO 96

O cágado-de-barbelas vive nas águas poluídas do Rio
'reto, em São José do Rio Preto, interior de São Paulo.
)s animais dessa espécie, usados em estudos de
'cotoxicologia, são atraídos para esses locais por causa
lo acúmulo de matéria orgânica nos pontos de despejo
le esgoto, ambientes com grande quantidade de metais
' baixíssimo teor de oxigênio.

Disponível em: www.unesp.br. Acesso em: 4 nov. 2014 (adaptado).
Jesse contexto, do ponto de vista ecológico, esses animais
ão considerados
) bioindicadores.

) biorremediadores.

À organismos invasores.

) anaeróbios facultativos.

3 decompositores adaptados.

REZA E AG TEAA BRABÕFRNADAOA
```
*Caracteres extraídos: 651*

**🤖 EASYOCR (GPU):**
```
[Confiança: 0.852] JUESTÃO 96
[Confiança: 0.799] cágado-de-barbelas vive nas águas poluídas do Rio
[Confiança: 0.463] Preto, em São José do Rio Preto, interior de São Paulo
[Confiança: 0.517] )s animais dessa espécie; usados em estudos de
[Confiança: 0.849] cotoxicologia; são atraídos para esses locais por causa
[Confiança: 0.494] lo acúmulo de matéria orgânica nos pontos de despejo
[Confiança: 0.658] le esgoto; ambientes com grande quantidade de metais
[Confiança: 0.928] baixíssimo teor de oxigênio
[Confiança: 0.666] Disponível em: www.unesp br. Acesso em: 4 nov. 2014 (adaptado) .
[Confiança: 0.896] esse contexto; do ponto de vista ecológico; esses animais
[Confiança: 0.997] ão considerados
[Confiança: 0.369] 0 bioindicadores -
[Confiança: 0.872] 3 biorremediadores .
[Confiança: 0.836] organismos invasores_
[Confiança: 0.844] 2 anaeróbios facultativos
[Confiança: 0.939] 2 decompositores adaptados
[Confiança: 0.130] ATUBf7l F
[Confiança: 0.142] Gua € TECNQI
[Confiança: 0.215] OGia
[Confiança: 0.303] anom
```
*Caracteres extraídos: 620 | Fragmentos: 20*

#### ✅ TEXTO FINAL SELECIONADO
```
o - k
VWESTÃO 96 - eec ;
O cágado-de-barbelas vive nas águas poluídas do Rio <(
'reto, em São José do Rio Preto, interior de São Paulo. f
)s animais dessa espécie, usados em estudos de — -
'cotoxicologia, são atraídos para esses locais por causa :
lo acúmulo de matéria orgânica nos pontos de despejo :
le esgoto, ambientes com grande quantidade de metais
: baixíssimo teor de oxigênio. i
Disponível em: www.unesp.br. Acesso em: 4 nov. 2014 (adaptado). j
Jesse contexto, do ponto de vista ecológico, esses animais í
ão considerados !
) bioindicadores. '
D biorremediadores. j
D organismos invasores. é
» anaeróbios facultativos. 1
3 decompositores adaptados. Í
aam — |
HA NATIIBEZA E SIHAS TECNOGOILOGIAS LQL NEABMAINNPOA
```
*Caracteres finais: 721*

#### 🧠 ANÁLISE OLLAMA (IA)
**✅ RESULTADO ESTRUTURADO:**
```json
{
  "question_number": 91,
  "question_text": "O cágado-de-barbelas vive nas águas poluídas do Rio <(reto, em São José do Rio Preto, interior de São Paulo. Os animais dessa espécie, usados em estudos de --toxicologia, são atraídos para esses locais por causa: o acúmulo de matéria orgânica nos pontos de despejo: le esgoto, ambientes com grande quantidade de metais: baixíssimo teor de oxigênio. Disponível em: www.unesp.br. Acesso em: 4 nov. 2014 (adaptado).",
  "alternatives": {
    "A": "",
    "B": "",
    "C": "",
    "D": "",
    "E": ""
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
O cágado-de-barbelas vive nas águas poluídas do Rio <(reto, em São José do Rio Preto, interior de São Paulo. Os animais dessa espécie, usados em estudos de --toxicologia, são atraídos para esses locais por causa: o acúmulo de matéria orgânica nos pontos de despejo: le esgoto, ambientes com grande quantidade de metais: baixíssimo teor de oxigênio. Disponível em: www.unesp.br. Acesso em: 4 nov. 2014 (adaptado).
```

**🔤 Alternativas:**
- **A)** 
- **B)** 
- **C)** 
- **D)** 
- **E)** 

---
### 📝 QUESTÃO DETECTADA #6

#### 📊 METADADOS DA DETECÇÃO
- **Número identificado:** Q93
- **Página original PDF:** 2
- **Posição (x,y,largura,altura):** (20, 1096, 552, 492)
- **Confiança da detecção:** 0.86

**🖼️ Imagem da região extraída:** `extracted_images\pagina_02_questao_Q93_6.png`
- **Dimensões da região:** 552x492 pixels

#### 🔤 EXTRAÇÃO OCR DETALHADA

**🔍 TESSERACT OCR:**
```
% graos de poilén numerosos.
QUESTÃO 93
Segundo especialistas, há uma ligação causal entr:
a ocupação nos 12 municípios do sistema de captaçã:
de água Cantareira, a destruição da mata ciliar de seu
8171 km de rios e o esgotamento do sistema. Choveu meno:
no último ano, mas, se a mata nativa ainda estivesse |á
os reservatórios poderiam ter mais água — e de melho
qualidade. Técnicos propõem o plantio de 30 milhões d
mudas para recompor a mata ciliar em 34 mil hectares.
SANT'ANNA, L. O Estado de S. Paulo, 21 fev. 2015 (adaptado
Essa ação está diretamente relacionada à prevenção do(a
O salinização da água.
O assoreamento do rio.
Q compactação do solo.
O contaminação das margens.
O eutrofização dos reservatórios.
2 mseesesseresermeroeroesremnoneoeosermrmseersemmeeseremeeemesesrerrao
59 DIA . CADERNO E . AMAREIO.GCIÊN
```
*Caracteres extraídos: 824*

**🤖 EASYOCR (GPU):**
```
[Confiança: 0.369] B graos ae polen numerosos_
[Confiança: 0.864] QUESTÃO 93
[Confiança: 0.784] Segundo especialistas; há uma ligação causal entre
[Confiança: 0.819] ocupação nos 12 municípios do sistema de captaçã
[Confiança: 0.801] de água Cantareira, a destruição da mata ciliar de seu
[Confiança: 0.797] 8171 km de rios e 0
[Confiança: 0.673] esgotamento do sistema: Choveu meno:
[Confiança: 0.739] no último ano; mas, se a mata nativa ainda estivesse
[Confiança: 0.867] os reservatórios poderiam ter mais água
[Confiança: 0.682] e de melho
[Confiança: 0.729] qualidade: Técnicos propõem 0 plantio de 30 milhões
[Confiança: 0.889] mudas para recompor a mata ciliar em 34 mil hectares_
[Confiança: 1.000] SANT'ANNA
[Confiança: 0.659] 0 Estado de S. Paulo, 21 fev. 2015 (adaptado
[Confiança: 0.713] Essa ação está diretamente relacionada à prevenção do(a
[Confiança: 0.730] salinização da água.
[Confiança: 0.691] assoreamento do rio
[Confiança: 0.973] compactação do solo.
[Confiança: 0.978] contaminação das margens _
[Confiança: 0.693] eutrofização dos reservatórios.
[Confiança: 0.378] 20 Dia
[Confiança: 0.196] CADfBnO 5
[Confiança: 0.156] Amabeio
[Confiança: 0.262] GIÊ
```
*Caracteres extraídos: 698 | Fragmentos: 24*

#### ✅ TEXTO FINAL SELECIONADO
```
1 graos dê porén NUMErosos.
QUESTÃO 93 - [2000000000000/0400/08080EAABAK80A
Segundo especialistas, há uma ligação causal entr:
a ocupação nos 12 municípios do sistema de captaçã:
de água Cantareira, a destruição da mata ciliar de seu
8171 km de rios e o esgotamento do sistema. Choveu meno:
no último ano, mas, se a mata nativa ainda estivesse lá
os reservatórios poderiam ter mais água — e de melho
qualidade. Técnicos propõem o plantio de 30 milhões d
mudas para recompor a mata ciliar em 34 mil hectares.
SANT'ANNA, L. O Estado de S. Paulo, 21 fev. 2015 (adaptado:
Essa ação está diretamente relacionada à prevenção do(a
O salinização da água.
O assoreamento do rio.
O compactação do solo.
O contaminação das margens.
Q eutrofização dos reservatórios.
AlDa eem
52 DIA L CANEDNGA B.AMABEIA ÊM
```
*Caracteres finais: 794*

#### 🧠 ANÁLISE OLLAMA (IA)
**❌ OLLAMA:** Falhou na estruturação (possível erro de formato JSON)

#### ❌ QUESTÃO NÃO ESTRUTURADA
Não foi possível estruturar esta questão (possível texto incompleto ou sem alternativas)

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
- **Posição (x,y,largura,altura):** (20, 112, 552, 810)
- **Confiança da detecção:** 1.00

**🖼️ Imagem da região extraída:** `extracted_images\pagina_03_questao_Q97_1.png`
- **Dimensões da região:** 552x810 pixels

#### 🔤 EXTRAÇÃO OCR DETALHADA

**🔍 TESSERACT OCR:**
```
QUESTÃO 97

O uso excessivo de embalagens plásticas ocasiono
um aumento na quantidade de resíduos plástico:
descartados no meio ambiente. Para minimizar o impact:
causado pelo acúmulo desses resíduos, pode-se emprega
alguns procedimentos:

|. Incineração;

Il. Reciclagem;

IIl. Acondicionamento em aterros sanitários;

IV. Substituição por plásticos biodegradáveis;

V. Substituição por plásticos oxibiodegradáveis.

Do ponto de vista ambiental, o procedimento adequad:

para solucionar o problema de acúmulo desses materiais «

O incinerar, pois isso reduz a quantidade de resíduos sólidos
e os gases liberados nesse processo não são poluentes

O reciclar, pois o plástico descartado é utilizado para :
produção de novos objetos, e isso evita a síntese de
maior quantidade de matéria-prima.

Q utilizar plásticos biodegradáveis, uma vez que :
matéria-prima é de fonte renovável e a produção desse:
materiais é simples e de baixo custo.

O dispensar em aterros sanitários, já que esses locais sãe
dimensionados para receber uma grande quantidade d.
resíduos e sua capacidade não se esgota rapidamente

O substituir por plásticos oxibiodegradáveis, visto que
ao serem descartados, são rapidamente assimilados pelo:
```
*Caracteres extraídos: 1215*

**🤖 EASYOCR (GPU):**
```
[Confiança: 1.000] QUESTÃO 97
[Confiança: 0.994] uso excessivo de
[Confiança: 0.866] embalagens plásticas ocasiono
[Confiança: 0.950] um aumento na quantidade de resíduos plástico
[Confiança: 0.797] descartados no meio ambiente. Para minimizar 0 impact
[Confiança: 0.678] causado pelo acúmulo desses resíduos, pode-se emprega
[Confiança: 0.644] alguns procedimentos:
[Confiança: 1.000] Incineração;
[Confiança: 0.843] Reciclagem;
[Confiança: 0.931] IIL
[Confiança: 0.817] Acondicionamento em aterros sanitários;
[Confiança: 0.958] IV.  Substituição por plásticos biodegradáveis;
[Confiança: 0.962] Substituição por plásticos oxibiodegradáveis.
[Confiança: 0.901] Do ponto de vista ambiental,
[Confiança: 0.994] procedimento adequad
[Confiança: 0.940] para solucionar 0
[Confiança: 0.985] problema de acúmulo desses materiais
[Confiança: 0.787] incinerar; pois isso reduz a quantidade de resíduos sólidos
[Confiança: 0.823] e os gases liberados nesse processo não são poluentes
[Confiança: 0.725] reciclar; pois 0 plástico descartado é utilizado para
[Confiança: 0.910] produção de novos objetos, e isso evita
[Confiança: 0.528] a síntese
[Confiança: 0.918] maior quantidade de matéria-prima.
[Confiança: 0.746] utilizar plásticos biodegradáveis, uma vez que
[Confiança: 0.589] matéria-prima é de fonte renovável e a produção desses
[Confiança: 0.677] materiais é simples e de baixo custo
[Confiança: 0.710] dispensar em aterros sanitários; já que esses locais sã
[Confiança: 0.993] dimensionados para receber uma grande quantidade
[Confiança: 0.949] resíduos e sua capacidade não se esgota rapidamente
[Confiança: 0.778] substituir por plásticos oxibiodegradáveis; visto que
[Confiança: 0.931] ao serem descartados; são rapidamente assimilados pelo
```
*Caracteres extraídos: 1129 | Fragmentos: 31*

#### ✅ TEXTO FINAL SELECIONADO
```
o TTn a tatmamanmeeamant—

| QUESTÃOS7 cccm aaa

l! O uso excessivo de embaltagens plásticas ocasiono:

') um aumento na quantidade de resíduos plástico:

i — descartadosnomeio ambiente. Para minimizar o impact:

í causado pelo acúmulo desses residuos, pode-se emprega

À alguns procedimentos:

lí' l. Incineração;

I1l. Reciclagem;

: Il. Acondicionamento em aterros sanitários;

| IV. Substituição por plásticos biodegradáveis;

À V. Substituição por plásticos oxibiodegradáveis.

)

: Do ponto de vista ambiental, o procedimento adequad:

J para solucionar o problema de acúmulo desses materiais «

Y

Ú O incinerar, pois isso reduz a quantidade de resíduos sólidos

À e os gases liberados nesse processo não são poluentes

; O reciclar, pois o plástico descartado é utilizado para :

3 produção de novos objetos, e isso evita a síntese d

j maior quantidade de matéria-prima.

d Q utilizar plásticos biodegradáveis, uma vez que :
matéria-prima é de fonte renovável e a produção desse:

À

; materiais é simples e de baixo custo.

l O dispensar em aterros sanitários, já que esses locais sãe

d dimensionados para receber uma grande quantidade d

i resíduos e sua capacidade não se esgota rapidamente

i Q substituir por plásticos oxibiodegradáveis, visto que

Ç ao serem descartados, são rapidamente assimilados pelo:
```
*Caracteres finais: 1321*

#### 🧠 ANÁLISE OLLAMA (IA)
**✅ RESULTADO ESTRUTURADO:**
```json
{
  "question_number": 91,
  "question_text": "O uso excessivo de embalagens plásticas ocasiona um aumento na quantidade de resíduos plástico descartados no ambiente. Para minimizar o impacto causado pelo acúmulo desses residuos, pode-se empregar alguns procedimentos: incineração; reciclagem; acondicionamento em aterros sanitários; substituição por plásticos biodegradáveis; ou substituição por plásticos oxibiodegradáveis. Do ponto de vista ambiental, o procedimento adequado para solucionar esse problema é?",
  "alternatives": {
    "A": "O incinerar, pois isso reduz a quantidade de resíduos sólidos e os gases liberados nesse processo não são poluentes.",
    "B": "O reciclar, pois o plástico descartado é utilizado para a produção de novos objetos, evitando a síntese de maior quantidade de matéria-prima.",
    "C": "O uso de materiais biodegradáveis, uma vez que a fonte renovável e a produção desses materiais é simples e de baixo custo.",
    "D": "O acondicionamento em aterros sanitários, já que esses locais são dimensionados para receber uma grande quantidade de resíduos e sua capacidade não se esgota rapidamente.",
    "E": "A substituição por plásticos oxibiodegradáveis, visto que eles são rapidamente assimilados pelo ambiente."
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
O uso excessivo de embalagens plásticas ocasiona um aumento na quantidade de resíduos plástico descartados no ambiente. Para minimizar o impacto causado pelo acúmulo desses residuos, pode-se empregar alguns procedimentos: incineração; reciclagem; acondicionamento em aterros sanitários; substituição por plásticos biodegradáveis; ou substituição por plásticos oxibiodegradáveis. Do ponto de vista ambiental, o procedimento adequado para solucionar esse problema é?
```

**🔤 Alternativas:**
- **A)** O incinerar, pois isso reduz a quantidade de resíduos sólidos e os gases liberados nesse processo não são poluentes.
- **B)** O reciclar, pois o plástico descartado é utilizado para a produção de novos objetos, evitando a síntese de maior quantidade de matéria-prima.
- **C)** O uso de materiais biodegradáveis, uma vez que a fonte renovável e a produção desses materiais é simples e de baixo custo.
- **D)** O acondicionamento em aterros sanitários, já que esses locais são dimensionados para receber uma grande quantidade de resíduos e sua capacidade não se esgota rapidamente.
- **E)** A substituição por plásticos oxibiodegradáveis, visto que eles são rapidamente assimilados pelo ambiente.

---
### 📝 QUESTÃO DETECTADA #2

#### 📊 METADADOS DA DETECÇÃO
- **Número identificado:** Q99
- **Página original PDF:** 3
- **Posição (x,y,largura,altura):** (612, 114, 552, 1200)
- **Confiança da detecção:** 0.69

**🖼️ Imagem da região extraída:** `extracted_images\pagina_03_questao_Q99_2.png`
- **Dimensões da região:** 552x1200 pixels

#### 🔤 EXTRAÇÃO OCR DETALHADA

**🔍 TESSERACT OCR:**
```
UESTÃO 99
Ao respirarmos, falarmos, tossirmos ou espirrarmos,
beramos gotículas e aerossóis. Se estamos com alguma
nfecção respiratória viral, vírus estarão contidos ali.
-stima-se que uma pessoa com covid-19 falando alto por
minuto pode gerar mais de 1 000 partículas de aerossóis,
) que poderia levar à liberação de mais de 100000 partículas
irais de SARS-CoV-2. O uso de máscaras pela população
ode auxiliar na redução da transmissão desse vírus,
onforme representado na figura.
Pessoa infectada Pessoas
assintomática saudáveis
... _' NE 20
a RE EE AAA
L
Exposição
máxima
Ç
Exposição
mínima
Disponível em: www:.blogs.unicamp.br.
Acesso em: 17 dez. 2021(adaptado).
s máscaras auxiliam no controle dessa doença, pois
D neutralizam as partículas virais presentes nas gotículas
e aerossóis.
) fornecem uma barreira de proteção contra as partículas
virais liberadas no ar.
3 reduzem a quantidade de vírus nas gotículas produzidas
durante a respiração.
» permitem que os indivíduos infectados inspirem e expirem
menos partículas virais.
3 mantêm afastados os indivíduos não infectados daqueles
que já foram infectados.
```
*Caracteres extraídos: 1116*

**🤖 EASYOCR (GPU):**
```
[Confiança: 0.960] JUESTÃO 99
[Confiança: 0.733] Ao respirarmos; falarmos, tossirmos ou espirrarmos
[Confiança: 0.758] beramos gotículas e aerossóis. Se estamos com alguma
[Confiança: 0.856] nfecção respiratória viral, vírus estarão contidos ali.
[Confiança: 0.781] Estima-se que uma pessoa com covid-19 falando alto por
[Confiança: 0.966] minuto pode gerar mais de
[Confiança: 0.814] 000 partículas de aerossóis_
[Confiança: 0.906] que poderia levar à liberação de mais de 100000 partículas
[Confiança: 0.363] 'irais de SARS-CoV-2.
[Confiança: 0.703] 0 uso de máscaras pela população
[Confiança: 0.948] ode auxiliar na redução da transmissão desse vírus,
[Confiança: 0.788] onforme representado na figura.
[Confiança: 0.815] Pessoa infectada
[Confiança: 0.999] Pessoas
[Confiança: 0.914] assintomática
[Confiança: 0.999] saudáveis
[Confiança: 1.000] Exposição
[Confiança: 0.998] máxima
[Confiança: 0.889] Exposição
[Confiança: 0.718] mínima
[Confiança: 0.658] Disponível em: www.b
[Confiança: 0.747] blogs.unicamp.br.
[Confiança: 1.000] Acesso em:
[Confiança: 0.869] dez. 2021(adaptado) 
[Confiança: 0.841] Is máscaras auxiliam no controle dessa doença; pois
[Confiança: 0.666] 0 neutralizam as partículas virais presentes nas gotículas
[Confiança: 0.679] e aerossóis _
[Confiança: 0.719] 2 fornecem uma barreira de proteção contra as partículas
[Confiança: 0.923] virais liberadas no ar.
[Confiança: 0.658] 9 reduzem a quantidade de vírus nas gotículas produzidas
[Confiança: 0.983] durante a respiração
[Confiança: 0.856] 2 permitem que os indivíduos infectados inspirem e expirem
[Confiança: 0.872] menos partículas virais_
[Confiança: 0.812] 2 mantêm afastados os indivíduos não infectados daqueles
[Confiança: 0.830] que já foram infectados
```
*Caracteres extraídos: 1047 | Fragmentos: 35*

#### ✅ TEXTO FINAL SELECIONADO
```
YWESTÃO 99 - Lsm
Ao respirarmos, falarmos, tossirmos ou espirrarmos,
beramos gotículas e aerossóis. Se estamos com alguma
nfecção respiratória viral, vírus estarão contidos ali.
-stima-se que uma pessoa com covid-19 falando alto por
minuto pode gerar mais de 1 000 partículas de aerossóis,
) que poderia levar à liberação de mais de 100000 partículas
irais de SARS-CoV-2. O uso de máscaras pela população
ode auxiliar na redução da transmissão desse vírus,
onforme representado na figura.
Pessoa infectada Pessoas
assintomática saudáveis:
Ás
Exposição.
máxima
SENE /xa úl d w
Exposição:
mínima
Disponível em: www.blogs.unicamp.br.
Acesso em: 17 dez. 2021(adaptado).
is máscaras auxiliam no controle dessa doença, pois
D neutralizam as partículas virais presentes nas gotículas
e aerossóis.
D fomecem uma barreira de proteção contra as partículas
virais liberadas no ar.
D reduzem a quantidade de vírus nas gotículas produzidas
durante a respiração.
» permitem que os indivíduos infectados inspirem e expirem
menos partículas virais.
3 mantêm afastados os indivíduos não infectados daqueles
que já foram infectados.
```
*Caracteres finais: 1114*

#### 🧠 ANÁLISE OLLAMA (IA)
**✅ RESULTADO ESTRUTURADO:**
```json
{
  "question_number": 91,
  "question_text": "A utilização de máscaras pela população pode auxiliar na redução da transmissão do SARS-CoV-2, pois elas neutralizam as partículas virais presentes nas gotículas e aerossóis, criando uma barreira de proteção contra as partículas virais liberadas no ar.",
  "alternatives": {
    "A": "As máscaras não auxiliam na redução da transmissão do SARS-CoV-2",
    "B": "As máscaras permitem que os indivíduos infectados inspirem e expirem mais partículas virais",
    "C": "As máscaras reduzem a quantidade de vírus nas gotículas produzidas durante a respiração",
    "D": "As máscaras criam uma barreira de proteção contra as partículas virais liberadas no ar, mas não reduzem a quantidade de vírus presentes nas gotículas"
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
A utilização de máscaras pela população pode auxiliar na redução da transmissão do SARS-CoV-2, pois elas neutralizam as partículas virais presentes nas gotículas e aerossóis, criando uma barreira de proteção contra as partículas virais liberadas no ar.
```

**🔤 Alternativas:**
- **A)** As máscaras não auxiliam na redução da transmissão do SARS-CoV-2
- **B)** As máscaras permitem que os indivíduos infectados inspirem e expirem mais partículas virais
- **C)** As máscaras reduzem a quantidade de vírus nas gotículas produzidas durante a respiração
- **D)** As máscaras criam uma barreira de proteção contra as partículas virais liberadas no ar, mas não reduzem a quantidade de vírus presentes nas gotículas

---
### 📝 QUESTÃO DETECTADA #3

#### 📊 METADADOS DA DETECÇÃO
- **Número identificado:** Q98
- **Página original PDF:** 3
- **Posição (x,y,largura,altura):** (20, 942, 552, 646)
- **Confiança da detecção:** 0.81

**🖼️ Imagem da região extraída:** `extracted_images\pagina_03_questao_Q98_3.png`
- **Dimensões da região:** 552x646 pixels

#### 🔤 EXTRAÇÃO OCR DETALHADA

**🔍 TESSERACT OCR:**
```
QUESTÃO 98
As lhamas que vivem nas montanhas dos Ande:
da América do Sul têm hemoglobinas geneticamente
diferenciadas de outros mamíferos que vivem ao níve
do mar, por exemplo. Essa diferenciação trata-se de um:
adaptação à sua sobrevivência em altitudes elevadas ond:
o ar é rarefeito.
SCHMIDT-NIELSEN, K. Fisiologia animal: adaptaçã
ao meio ambiente. São Paulo: Santos, 2007
A adaptação desses animais em relação ao seu ambient:
confere maior
O afinidade pelo O,, maximizando a captação desse gás
O capacidade de tamponamento, evitando alterações d:
PH no sangue.
Q afinidade pelo CO,, facilitando seu transporte par:
eliminação nos pulmões.
O velocidade no transporte de gases, aumentando :
eficiência de troca gasosa.
O solubilidade de gases no plasma, melhorando sei
transporte nos tecidos.
BRSIROAOA o n ANn EMA EN
```
*Caracteres extraídos: 821*

**🤖 EASYOCR (GPU):**
```
[Confiança: 0.805] QUESTÃO 98
[Confiança: 0.684] As Ihamas que vivem nas montanhas dos Ande
[Confiança: 0.699] da América do Sul têm hemoglobinas geneticamente
[Confiança: 0.688] diferenciadas de outros mamíferos que vivem ao níve
[Confiança: 0.660] do mar; por exemplo. Essa diferenciação trata-se de uma
[Confiança: 0.874] adaptação à sua sobrevivência em altitudes elevadas ond
[Confiança: 0.876] ar é rarefeito_
[Confiança: 0.987] SCHMIDT-NIELSEN, K
[Confiança: 0.999] Fisiologia animal: adaptaçã
[Confiança: 0.786] ao meio ambiente. São Paulo: Santos
[Confiança: 0.980] 2002
[Confiança: 0.794] Aadaptação desses animais em relação ao seu ambiente
[Confiança: 0.893] confere maior
[Confiança: 0.821] afinidade pelo O2' maximizando a captação desse gá-
[Confiança: 0.887] capacidade de tamponamento; evitando alterações
[Confiança: 0.996] pH no sangue
[Confiança: 0.867] afinidade pelo CO2' facilitando seu transporte par
[Confiança: 0.803] eliminação nos pulmões
[Confiança: 0.768] D velocidade no transporte de gases, aumentando
[Confiança: 0.776] eficiência de troca gasosa
[Confiança: 0.900] solubilidade de gases no plasma, melhorando
[Confiança: 0.778] transporte nos tecidos
[Confiança: 0.067] Pne
[Confiança: 0.282] Ooo
[Confiança: 0.380] 20 Dia
[Confiança: 0.076] CADfBNO
```
*Caracteres extraídos: 764 | Fragmentos: 26*

#### ✅ TEXTO FINAL SELECIONADO
```
7 "

ª QUESTÃO 98 - Le2220000/0/000000000000/EUA SAA
j As lhamas que vivem nas montanhas dos Ande:
' — daAméricado Sul têm hemoglobinas geneticament:
À diferenciadas de outros mamíferos que vivem ao níve
J do mar, por exemplo. Essa diferenciação trata-se de um:
: adaptação à sua sobrevivência em altitudes elevadas ond:
i  oarérarefeito.

i SCHMIDT-NIELSEN, K. Fisiologia animal: adaptaçã
? ao meio ambiente. São Paulo: Santos, 200
;

3 A adaptação desses animais em relação ao seu ambient:
;  Conferemaior

d O afinidade pelo O,, maximizando a captação desse gás
; O capacidade de tamponamento, evitando alterações d:
j PpH no sangue.

| Q& afinidade pelo CO,, facilitando seu transporte par:
I_ eliminação nos pulmões.

: O velocidade no transporte de gases, aumentando :
Y eficiência de troca gasosa.

? Q solubilidade de gases no plasma, melhorando se:
! transporte nos tecidos.

j

UU ressaemnmameniaremanateemanamieamtremmearmemmeaí—c
o BNBMIRAINOA 52 DIA L CANEDNGA B.AMABEIA . CIÊM
```
*Caracteres finais: 990*

#### 🧠 ANÁLISE OLLAMA (IA)
**✅ RESULTADO ESTRUTURADO:**
```json
{
  "question_number": 98,
  "question_text": "Enunciado completo: As lhamas que vivem nas montanhas dos Andes têm hemoglobinas geneticamente diferenciadas de outros mamíferos que vivem ao nível do mar, como por exemplo, o homem. Essa diferenciação se trata de uma adaptação à sua sobrevivência em altitudes elevadas, que afeta a capacidade de tamponamento, evitando alterações de pH no sangue.",
  "alternatives": {
    "A": "Alternativa A: A adaptação desses animais em relação ao seu ambiente é uma resposta adaptativa genética",
    "B": "Alternativa B: A afinidade pelo O2, maximizando a captação desse gás no sangue.",
    "C": "Alternativa C: O capacidade de tamponamento, evitando alterações de pH no sangue, aumentando a eficiência de troca gasosa",
    "D": "Alternativa D: A solubilidade de gases no plasma, melhorando o transporte nos tecidos",
    "E": "Alternativa E: Uma explicação para essa adaptação é que os animais vivem em ambientes com altitudes elevadas"
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
Enunciado completo: As lhamas que vivem nas montanhas dos Andes têm hemoglobinas geneticamente diferenciadas de outros mamíferos que vivem ao nível do mar, como por exemplo, o homem. Essa diferenciação se trata de uma adaptação à sua sobrevivência em altitudes elevadas, que afeta a capacidade de tamponamento, evitando alterações de pH no sangue.
```

**🔤 Alternativas:**
- **A)** Alternativa A: A adaptação desses animais em relação ao seu ambiente é uma resposta adaptativa genética
- **B)** Alternativa B: A afinidade pelo O2, maximizando a captação desse gás no sangue.
- **C)** Alternativa C: O capacidade de tamponamento, evitando alterações de pH no sangue, aumentando a eficiência de troca gasosa
- **D)** Alternativa D: A solubilidade de gases no plasma, melhorando o transporte nos tecidos
- **E)** Alternativa E: Uma explicação para essa adaptação é que os animais vivem em ambientes com altitudes elevadas

---

# 📊 RESUMO FINAL DA EXTRAÇÃO

## 🎯 ESTATÍSTICAS
- **Total de questões extraídas:** 8
- **Páginas processadas:** 2
- **Expectativa ENEM:** 90-95 questões por caderno
- **Taxa de extração:** 8.9% do esperado

## 📋 QUESTÕES IDENTIFICADAS
**Números das questões:** [91, 92, 98]
