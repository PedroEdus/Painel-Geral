# QRFY Public API — Referência completa (não-oficial)

Levantada a partir da especificação OpenAPI 3.0 oficial da QRFY (`qrfy.com/public-api-specification.json`), da documentação renderizada em `qrfy.com/docs`, e de uma chamada real de teste contra `/api/public/qrs` para confirmar host e formato de erro. Onde a especificação oficial era ambígua ou inconsistente, isso está sinalizado na seção **Notas & inconsistências** no final, em vez de ser "corrigido" silenciosamente.

## Sumário

1. [Autenticação](#1-autenticação)
2. [URL base & limites de uso](#2-url-base--limites-de-uso)
3. [Formato de erros](#3-formato-de-erros)
4. [Endpoints — QR codes](#4-endpoints--qr-codes)
5. [Endpoints — Pastas](#5-endpoints--pastas)
6. [Objeto `style` (aparência do QR)](#6-objeto-style--aparência-do-qr)
7. [Tipos de QR & schema de `data`](#7-tipos-de-qr--schema-de-data)
8. [Notas & inconsistências da especificação](#8-notas--inconsistências-da-especificação)

---

## 1. Autenticação

Toda chamada é autenticada por uma **API key estática** enviada em um header HTTP — não há OAuth, não há tokens temporários.

| Header | Tipo | Descrição |
|---|---|---|
| `API-KEY` | string | Sua chave de API. Obrigatória em praticamente todos os endpoints. |

**Como gerar a chave:** dentro da sua conta QRFY, vá em `Settings → API key → Generate API key`. Isso cria uma credencial de segurança — cada conta tem apenas uma chave ativa por vez, e regenerá-la invalida a anterior (qualquer integração usando a chave antiga passa a receber `401`).

**Exemplo de requisição autenticada:**

```bash
curl https://qrfy.com/api/public/qrs \
  -H "API-KEY: sua_chave_aqui"
```

---

## 2. URL base & limites de uso

**URL base:**

```
https://qrfy.com/api/public
```

A especificação OpenAPI não declara um campo `servers` — todos os `paths` são relativos. O host foi confirmado testando `GET /api/public/qrs` diretamente contra `qrfy.com`.

**Limite de requisições:** a QRFY não publica o número exato de requisições/dia na especificação. A própria página de docs orienta: *"Do you need more requests? Please contact us if you need more requests per day for individuals or commercial use."* — ou seja, existe uma cota por padrão, mas o valor não é público; aumentos são negociados com o suporte.

---

## 3. Formato de erros

Testado ao vivo enviando uma chave inválida:

```bash
curl -i https://qrfy.com/api/public/qrs \
  -H "API-KEY: chave-invalida"
```

Resposta real (`401`):

```json
{
  "error": true,
  "message": "Invalid API key",
  "errorCode": "invalid_api_key",
  "uuid": "17b59740-4d91-4e52-ae51-4fae534fc274"
}
```

Status declarados na especificação por endpoint (só o `401` foi verificado ao vivo; os demais vêm direto do OpenAPI):

| Status | Quando ocorre |
|---|---|
| `400` | Validation Failed — corpo da requisição não passou na validação de schema. |
| `401` | Invalid API key — header `API-KEY` ausente ou incorreto. |
| `404` | Recurso não encontrado (QR, pasta ou imagem inexistente). |
| `409` | Conflict — apenas em `PUT /qrs/{id}`, ao tentar trocar um QR entre tipo dinâmico e estático. |

---

## 4. Endpoints — QR codes

Todos sob `/api/public/qrs`.

### `POST /api/public/qrs` — Criar QR codes em lote

Cria vários QR codes em uma única chamada, cada um com seu próprio tipo e conteúdo.

**Body:**

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `qrs` | array | ✅ | Lista de QR codes a criar. |
| `qrs[].type` | enum | ✅ | Um dos 21 tipos — ver [seção 7](#7-tipos-de-qr--schema-de-data). |
| `qrs[].data` | object | ✅ | Payload específico do tipo escolhido. |
| `qrs[].name` | string | – | Nome exibido no painel (máx. 100 caracteres). |
| `qrs[].folder` | integer | – | ID da pasta de destino. |
| `qrs[].style` | object | – | Sobrescreve o `style` global para este item. |
| `qrs[].accessPassword` | string | – | Protege o QR com senha (mín. 3 caracteres). |
| `qrs[].scanLimit` | integer | – | Limite de leituras (1 a 10.000.000). |
| `qrs[].hostname` | string | – | Subdomínio customizado. |
| `qrs[].googleAnalyticsId` / `facebookPixelId` / `googleTagManagerId` | string | – | IDs de rastreamento aplicados à página do QR. |
| `style` | object | – | Estilo visual aplicado a todos os QRs do lote (pode ser sobrescrito por item). |
| `folder` | integer | – | Pasta padrão do lote. |

**Exemplo — um QR "url" e um "wifi":**

```json
{
  "qrs": [
    {
      "name": "Cardápio digital",
      "type": "url",
      "data": { "url": "https://qrfy.com" }
    },
    {
      "name": "WIFI",
      "type": "wifi",
      "data": { "authType": "WEP", "ssid": "My wifi", "hidden": false }
    }
  ],
  "style": {
    "shape": { "backgroundColor": "#ffffff", "color": "#000000", "style": "square" },
    "corners": { "squareStyle": "square", "dotStyle": "square", "dotColor": "#000000", "squareColor": "#000000" }
  }
}
```

**Resposta — `200 Created`:**

```json
{ "ids": [101, 102] }
```

| Status | Significado |
|---|---|
| `200` | Criado — retorna os IDs na mesma ordem enviada. |
| `400` | Validation Failed. |
| `401` | Invalid API key. |
| `404` | A pasta informada em `folder` não existe. |

---

### `PUT /api/public/qrs` — Editar QR codes em lote

Mesma forma do create, mas cada item exige `id`.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `qrs` | array | ✅ | Lista de QRs a atualizar. |
| `qrs[].id` | integer | ✅ | ID do QR existente. |
| `qrs[].type` / `data` | enum / object | ✅ | Mesmas regras do create. |
| demais campos | — | – | Idênticos ao bulk create. |

**Resposta — `200 Ok`:** array completo de objetos `QRItem` atualizados.

```json
[
  {
    "id": 101,
    "name": "Cardápio digital",
    "type": "url",
    "data": { "url": "https://qrfy.com" },
    "status": true,
    "scans": 0,
    "createdAt": 1693257323,
    "updatedAt": 1693257400
  }
]
```

Erros: `400`, `401`, `404`.

---

### `GET /api/public/qrs` — Listar QR codes

Paginação e filtros.

| Query param | Tipo | Descrição |
|---|---|---|
| `page` | integer | Número da página. |
| `sortBy` | enum | `name` · `created_at` · `updated_at` · `scans`. Ordem decrescente, exceto para `name`. |
| `folder` | integer | Filtra por ID de pasta. |
| `types` | array | Filtra por um ou mais tipos. |
| `status` | enum | `active` · `soft-deleted` · `stopped` · `blocked`. |
| `searchTerm` | string | Busca por nome. |

**Resposta — `200 OK`:**

```json
{
  "pages": 3,
  "total": 57,
  "data": [
    {
      "id": 101,
      "name": "Cardápio digital",
      "type": "url",
      "status": true,
      "scans": 42,
      "finalUrl": "https://qrfy.com/r/abc123",
      "createdAt": 1693257323
    }
  ]
}
```

---

### `GET /api/public/qrs/{id}` — Obter um QR code

Path param: `id` (integer). Resposta: um objeto `QRItem` completo (mesma forma da listagem). Erros: `401`, `404`.

---

### `PUT /api/public/qrs/{id}` — Atualizar um QR code

Aceita os mesmos campos do item de bulk create (`name`, `folder`, `type`, `data`, `style`, `accessPassword`, IDs de rastreamento, `hostname`, `scanLimit`), sem o wrapper `qrs`.

**Resposta — `200 Ok`:**

```json
{ "id": 101, "raw": "https://qrfy.com/r/abc123" }
```

| Status | Significado |
|---|---|
| `401` | Invalid API key. |
| `404` | QR não encontrado. |
| `409` | Conflict — não é permitido trocar um QR entre dinâmico e estático (ex.: de `url` para `url-static`). |

---

### `POST /api/public/qrs/{id}/duplicate` — Duplicar um QR code

Path param: `id`. Resposta `200`: `{ "id": 1 }` — o ID da cópia criada. Erros: `401`, `404`.

---

### `POST /api/public/qrs/{format}` — Gerar imagem de QR avulsa (sem salvar)

Path param `format`: `webp` · `png` · `jpeg`. Útil para gerar QRs on-the-fly sem poluir a lista de QRs salvos.

| Campo (body) | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `type` | enum | ✅ | Apenas tipos estáticos — ver nota abaixo. |
| `data` | object | ✅ | Payload do tipo (email, sms, text, url-static, vcard, wifi ou whatsapp). |
| `style` | object | ✅ | Ver [seção 6](#6-objeto-style--aparência-do-qr). |

> ⚠️ A especificação lista o enum de `type` literalmente como `["email sms", "text", "url-static", "vcard", "whatsapp", "wifi"]` — o valor `"email sms"` (com espaço) parece um typo da própria QRFY que deveria ser dois valores separados, `email` e `sms`. Se `email` ou `sms` isolados forem rejeitados, é essa a causa provável.

Resposta `200`: a imagem binária (`image/webp`, `image/png` ou `image/jpeg`). Erros: `400`, `401`.

---

### `GET /api/public/qrs/{id}/{format}` — Baixar imagem de um QR salvo

Path params: `id` e `format` (`webp` · `png` · `jpeg`). Resposta `200`: imagem binária. `404` se o QR não existir.

---

### `POST /api/public/qrs/batch-delete` — Excluir QR codes em lote ⚠️ destrutivo

```json
{ "ids": [101, 102, 103] }
```

`ids` — array de integers, obrigatório, itens únicos. Resposta: `204 No Content`. Erros: `401`, `404`. Não há endpoint de exclusão reversível — trate como definitivo.

---

### `GET /api/public/qrs/report` — Relatório de leituras (scans)

| Query param | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `from` | integer (unix ts) | ✅ | Início do período. |
| `to` | integer (unix ts) | ✅ | Fim do período. |
| `format` | enum | ✅ | `json` · `csv` · `xlsx`. |
| `ids[]` | array\<integer\> | – | Restringe a QR codes específicos. |
| `folders[]` | array\<integer\> | – | Restringe a pastas específicas. |
| `type` | enum | – | `detailed` (padrão) ou `totals`. |
| `grouping` | enum | – | `daily` (padrão) · `monthly` · `yearly` — só se aplica quando `type=totals`. |

```bash
curl "https://qrfy.com/api/public/qrs/report?from=1690000000&to=1700000000&format=json&type=totals&grouping=monthly" \
  -H "API-KEY: sua_chave_aqui"
```

O `Content-Type` da resposta muda conforme `format`: `application/json`, `application/csv` ou `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (xlsx binário).

---

## 5. Endpoints — Pastas

Organização simples em pastas. Sem subpastas nem endpoints de edição/exclusão documentados na especificação pública.

### `POST /api/public/folders` — Criar uma pasta

```json
{ "name": "Campanha de verão" }
```

`name` — string, obrigatório, máx. 100 caracteres. Resposta `200`: `{ "id": 8 }`. Erros: `400`, `401`.

### `GET /api/public/folders` — Listar pastas

```json
[
  { "id": 8, "name": "Campanha de verão", "qrs": 12, "createdAt": "2022-11-01T20:51:14.000Z" }
]
```

---

## 6. Objeto `style` (aparência do QR)

Compartilhado por todos os endpoints que criam ou editam QRs. Controla cor, forma dos módulos, estilo dos cantos, moldura (frame) e nível de correção de erro.

| Campo | Tipo | Valores / padrão |
|---|---|---|
| `image` | string (URL) | Logo central sobreposto ao QR. |
| `shape.backgroundColor` | Color \| Gradient \| `"transparent"` | Padrão `#ffffff`. |
| `shape.color` | Color \| Gradient | Padrão `#000000`. |
| `shape.style` | enum | `square` (padrão) · rounded · dots · classy · classy-rounded · extra-rounded · cross · cross-rounded · diamond · diamond-special · heart · horizontal-rounded · ribbon · shake · sparkle · star · vertical-rounded · x · x-rounded |
| `corners.squareStyle` | enum | `square` (padrão) · default · dot · extra-rounded · shape1…shape12 |
| `corners.dotStyle` | enum | `square` (padrão) · default · dot · cross · cross-rounded · diamond · dot2-4 · heart · rounded · square2-3 · star · sun · x · x-rounded |
| `corners.dotColor` / `squareColor` | Color \| Gradient | Padrão `#000000`. |
| `frame` | object \| null | Se presente, exige `id` (0–30), `color`, `text` (máx. 30 car.), `fontSize` (30–98). |
| `errorCorrectionLevel` | enum | `L` · `M` · `Q` (padrão) · `H` |

**Color / Gradient:** onde o tipo é `Color \| Gradient`, aceita uma cor hex simples (`"#FF0000"`) ou um objeto de gradiente:

```json
{
  "type": "linear",
  "rotation": 45,
  "colorStops": [
    { "offset": 0, "color": "#2F6BFD" },
    { "offset": 1, "color": "#0E379A" }
  ]
}
```

**Exemplo completo:**

```json
{
  "image": "",
  "shape": { "backgroundColor": "#ffffff", "color": "#000000", "style": "square" },
  "corners": { "squareStyle": "square", "dotStyle": "square", "dotColor": "#000000", "squareColor": "#000000" },
  "frame": null,
  "errorCorrectionLevel": "Q"
}
```

---

## 7. Tipos de QR & schema de `data`

O campo `data` muda de forma conforme `type`. A maioria dos exemplos abaixo vem dos exemplos oficiais da especificação (levemente resumidos); os tipos sem exemplo oficial publicado mostram apenas os campos declarados no schema. Campos marcados com `*` são obrigatórios.

### `app` — Página de divulgação de um aplicativo

Campos: `name*`, `developer`, `logo`, `description`, `apps*`, `preview`, `design*`

```json
{
  "name": "Myfintech",
  "developer": "Tech & Corp",
  "logo": "https://qrfy.com/csv-examples/app_logo.svg",
  "description": "Control all your finances easily and quickly.",
  "website": "https://qrfy.com",
  "apps": { "iphone": "https://apps.apple.com", "android": "https://play.google.com", "amazon": "https://amazon.com" },
  "design": { "primary": "#111111", "secondary": "#6D6D6D" }
}
```

### `business` — Perfil de estabelecimento

Campos: `design*`, `title*`, `image`, `company`, `subtitle`, `schedule`, `button`, `address`, `companyName`, `companyPhoneNumber`, `companyEmail`, `companyWebsite`, `facilities`, `socialsTitle`, `socials`

```json
{
  "title": "Morning Star Cafe",
  "design": { "primary": "#0E379A", "secondary": "#000000" },
  "company": "Specialty coffee",
  "subtitle": "Natural, artisan and local coffee. Open Tue–Sun, 8am–7pm.",
  "button": { "text": "Order online", "url": "https://qrfy.com" },
  "facilities": ["wifi", "seat", "toilet", "cafe", "bar", "restaurant"],
  "address": {
    "type": "full",
    "data": { "street": "Street", "number": 555, "city": "Barcelona", "country": "Spain" }
  },
  "schedule": {
    "format": "24hs",
    "monday": [{ "from": "08:00", "to": "15:00" }, { "from": "16:00", "to": "18:00" }]
  }
}
```

### `coupon` — Cupom de desconto

Campos: `design*`, `title*`, `validUntil*`, `button*`, `banner`, `company`, `description`, `showCodeButton`, `badge`, `coupon`, `barcode`, `termsAndConditions`, `address`

```json
{
  "design": { "primary": "#545454", "secondary": "#FF3434" },
  "banner": { "image": "https://qrfy.com/csv-examples/coupon.webp", "size": 100, "background": "#FFFFFF" },
  "company": "Electrofy",
  "title": "25% OFF",
  "description": "Use this coupon in all technology products",
  "showCodeButton": "Get coupon",
  "coupon": "SALE25OFF",
  "validUntil": 1700789480,
  "button": { "text": "Redeem now", "url": "https://qrfy.com" }
}
```

### `event` — Divulgação de evento

Campos: `design*`, `title*`, `image`, `description`, `button`, `address`, `organizerName`, `organizerPhoneNumber`, `organizerEmail`, `organizerWebsite`, `facilities`, `eventDate`, `addCalendarButton`

### `feedback` — Formulário de avaliação/satisfação

Campos: `design*`, `name*`, `categories*`, `title`, `emailEnabled`, `email`, `website`, `ratingsDisabled`

Ícones de categoria (`FeedbackIcon`) vêm de uma lista fixa: `ambience`, `asterisk`, `bar`, `bed`, `calendar`, `cart`, `cash`, `chat`, `check`, `clock`, `group`, `housekeeping`, `info`, `location`, `parking`, `restaurant`, `restore`, `room_service`, `seat`, `settings`, `spa`, `toilet`, `user`, `wifi`.

### `images` — Galeria/carrossel de fotos

Campos: `images*`, `design*`, `title`, `description`, `url`, `buttons`, `templateType`

```json
{
  "title": "Our wedding",
  "description": "Words can't express the love we have for one another.",
  "design": { "color": "#132272" },
  "buttons": [{ "text": "Download", "url": "https://qrfy.com" }],
  "templateType": "carousel",
  "images": ["https://qrfy.com/csv-examples/images1.webp", "https://qrfy.com/csv-examples/images2.webp"]
}
```

### `link-list` — Página de links (estilo "linktree")

Campos: `design*`, `links*`, `socials*`, `title`, `description`, `logo`, `socialsTitle`

```json
{
  "title": "Takeshi Fujimoto",
  "description": "Gourmet recipes",
  "design": { "primary": "#1B1B1B", "secondary": "#3E3E3E", "tertiary": "#EDFF7C" },
  "links": [
    { "text": "Basket egg", "url": "https://qrfy.com", "photo": "https://qrfy.com/csv-examples/link1.webp" },
    { "text": "Shoyu Ramen", "url": "https://qrfy.com", "photo": "https://qrfy.com/csv-examples/link2.webp" }
  ]
}
```

### `menu` — Cardápio digital

Campos: `design*`, `sections*`, `languages`, `title`, `description`, `socialsTitle`, `socials`, `logo`

> ⚠️ A especificação marca `items` como obrigatório, mas esse nome não aparece na lista de propriedades declaradas — os exemplos reais usam `sections`. Use `sections`.

```json
{
  "title": "Don Tulio",
  "design": { "primary": "#2F6BFD", "secondary": "#0E379A" },
  "description": "Our selection of burgers will surprise you.",
  "sections": [{
    "name": "Starters",
    "items": [{
      "name": "T-Bone",
      "image": "https://qrfy.com/csv-examples/menu1.webp",
      "description": "Assortment of grilled meats",
      "price": "65€",
      "allergens": ["celery"]
    }]
  }]
}
```

### `mp3` — Player de áudio

Campos: `design*`, `title`, `description`, `mp3`, `image`, `website`, `button`, `downloadOption`

```json
{
  "title": "Rain cover",
  "mp3": "https://qrfy.com/csv-examples/audio.mp3",
  "design": { "primary": "#0E379A", "secondary": "#000000" },
  "image": "https://qrfy.com/csv-examples/mp3.webp",
  "description": "My group"
}
```

### `pdf` — Visualizador de PDF

Campos: `pdfs*`, `design*`, `org`, `title`, `description`, `web`, `directPdfLink`, `button`

```json
{
  "org": "Los Burgueses",
  "title": "Las Burgers",
  "description": "Our selection of burgers will surprise you.",
  "design": { "primary": "#2F6BFD", "secondary": "#0E379A" },
  "web": "https://qrfy.com",
  "button": "PDF",
  "directPdfLink": false
}
```

O campo declarado no schema é `pdfs` (plural) — o exemplo oficial não mostra seu conteúdo, mas pelo padrão dos demais tipos deve ser a URL do arquivo (possivelmente um array).

### `video` — Player de vídeo (upload próprio ou YouTube)

Campos: `videos*`, `design*`, `org`, `title`, `description`, `markFirstVideo`, `directVideoLink`, `autoplay`, `button`

```json
{
  "title": "Tech & Corp Manifesto",
  "design": { "color": "#0E379A" },
  "videos": [
    { "type": "self-hosted", "description": "Self hosted video", "url": "https://qrfy.com/csv-examples/video.mp4" },
    { "type": "youtube", "description": "Youtube video", "url": "https://www.youtube.com/watch?v=..." }
  ]
}
```

### `social` — Hub de redes sociais

Campos: `design*`, `socials*`, `title`, `description`, `phone`, `pageTemplateId`, `email`, `website`, `logo`, `coverImage`

> ⚠️ O schema marca `links` como obrigatório junto de `design`/`socials`, mas `links` também não consta nas propriedades declaradas — mesmo padrão de inconsistência do tipo `menu`. Provavelmente equivale ao objeto `socials` (lista de redes, mesmo formato de `SocialNetworkList` usado em outros tipos).

### `barcode` — Código de barras GS1 (2D)

Campos: `gtin*`, `url*`

### `vcard-plus` — Cartão de visita digital (completo/dinâmico)

Campos: `name*`, `design*`, `address`, `phone`, `email`, `lastName`, `photo`, `companies`, `shareButton`, `socialsTitle`, `socials`, `summary`, `title`, `url`

```json
{
  "design": { "primary": "#0E379A", "secondary": "#000000" },
  "photo": "https://qrfy.com/csv-examples/vcard.webp",
  "name": "Alvaro",
  "lastName": "Muñoz",
  "phone": [{ "type": "work", "text": "Landline", "phone": "555-5555" }],
  "email": [{ "text": "Email", "email": "support@qrfy.com" }],
  "org": "QRFY",
  "title": "CEO",
  "summary": "More than fifteen years of experience..."
}
```

### `vcard` — Cartão de visita estático (vCard clássico)

Campos: `name*`, `lastname`, `phone`, `email`, `org`, `title`, `adr`, `city`, `zip`, `state`, `country`, `url`

### `wifi` — Conecta direto a uma rede Wi-Fi

Campos: `authType*`, `ssid*`, `password`, `hidden`

```json
{ "authType": "WEP", "ssid": "My wifi", "hidden": false }
```

### `text` — Texto simples

Campos: `text*`

```json
{ "text": "hello" }
```

### `url` / `url-static` — Redireciona para um link

`url` é dinâmico (editável depois); `url-static` é fixo no QR.

Campos: `url*`

```json
{ "url": "https://qrfy.com" }
```

### `email` — Abre um rascunho de e-mail pré-preenchido

Campos: `email*`, `subject`, `body`, `hidden`

### `sms` — Abre um rascunho de SMS

Campos: `number*`, `message`

### `whatsapp` — Abre uma conversa no WhatsApp

Campos: `number*`, `message`

---

## 8. Notas & inconsistências da especificação

Para não passar informação incerta como fato, tudo que pareceu inconsistente na especificação oficial está listado aqui, em vez de "corrigido" silenciosamente.

| Onde | O que se observa |
|---|---|
| `QrStaticType` | Enum inclui `"email sms"` como um único valor (com espaço) em vez de `"email"` e `"sms"` separados. Provável typo da QRFY. |
| `MenuBody` | `required` cita `items`, mas a lista de propriedades não tem esse nome — os exemplos reais usam `sections`. |
| `SocialBody` | `required` cita `links`, ausente das propriedades declaradas; nenhum exemplo oficial de `social` foi publicado para confirmar o nome real do campo. |
| `servers` | A spec OpenAPI não declara um bloco `servers`/host — o domínio `qrfy.com` foi confirmado por chamada real, não pela especificação. |
| Rate limit | Nenhum número de requisições/dia é publicado; só a orientação genérica de contatar o suporte para aumentar a cota. |

---

*Compilado a partir de [qrfy.com/public-api-specification.json](https://qrfy.com/public-api-specification.json) e [qrfy.com/docs](https://qrfy.com/docs) · não é um documento oficial da QRFY.*
