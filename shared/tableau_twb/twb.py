"""Minimal, dependency-free writer for Tableau workbook XML (.twb, version 18.1 / Tableau 2026.x).

Why: the environment has no tool that can drive Tableau Desktop, so the workbooks are generated as files that
Tableau Public opens directly (File > Open). The format mirrors a workbook saved by Tableau 2026.3 on this machine
(text-file connections, parameters, categorical filters, column instances). Dashboards use floating zones.

Field references
----------------
    F("year")                 discrete dimension        -> [none:year:ok]   (kind='ok' ordinal, 'nk' nominal)
    F("sale_value_brl","sum") aggregated measure        -> [sum:sale_value_brl:qk]
    F("period_date","tmn")    continuous month          -> [tmn:period_date:qk]
    F("KPI Value")            calculated field by caption; aggregate calcs become [usr:Calculation_N:qk]
Formulas reference other calculations by caption with {{Caption}} and parameters with {{p Year}}.
"""
from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from xml.sax.saxutils import escape, quoteattr

AGG = {"sum": ("Sum", "qk"), "avg": ("Avg", "qk"), "max": ("Max", "qk"), "min": ("Min", "qk"),
       "cnt": ("Count", "qk"), "cntd": ("CountD", "qk"), "tmn": ("Month-Trunc", "qk"), "yr": ("Year", "ok"), "tyr": ("Year-Trunc", "qk"),
       "attr": ("Attribute", "nk")}
AGG_FUNCS = re.compile(r"\b(SUM|AVG|MIN|MAX|COUNT|COUNTD|ATTR|TOTAL|RUNNING_SUM|LOOKUP|RANK|WINDOW_\w+)\s*\(", re.I)


def _bucket(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)) or v in ("true", "false"):
        return str(v)
    return '"' + str(v) + '"'


def q(v) -> str:
    return quoteattr(str(v))


def _id(*parts: str, n: int = 28) -> str:
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()   # 64 hex chars -> up to 32 id chars
    return "".join("0123456789abcdefghijklmnopqrstuvwxyz"[int(h[i:i + 2], 16) % 36] for i in range(0, 2 * n, 2))


def _uuid(*parts: str) -> str:
    return "{" + str(uuid.uuid5(uuid.NAMESPACE_URL, "|".join(parts))).upper() + "}"


@dataclass(frozen=True)
class F:
    name: str
    agg: str | None = None
    kind: str | None = None          # for dimensions: 'ok' (ordinal) or 'nk' (nominal)


@dataclass
class Column:
    name: str
    datatype: str                    # string | integer | real | date | boolean
    role: str                        # dimension | measure
    type: str                        # nominal | ordinal | quantitative
    caption: str | None = None
    formula: str | None = None
    default_format: str | None = None
    is_aggregate: bool = False
    semantic_role: str | None = None


class Parameters:
    NAME = "Parameters"

    def __init__(self):
        self.cols: dict[str, Column] = {}
        self.extra: dict[str, str] = {}

    def add(self, caption: str, datatype: str, value, members: list | None = None, fmt: str | None = None) -> str:
        name = f"[Parameter {len(self.cols) + 1}]"
        lit = (f'"{value}"' if datatype == "string" else str(value))
        c = Column(name, datatype, "measure", "nominal" if datatype == "string" else "quantitative",
                   caption=caption, formula=lit, default_format=fmt)
        self.cols[caption] = c
        mem = ""
        if members is not None:
            ms = "".join(f"<member value={q(chr(34) + str(m) + chr(34) if datatype == 'string' else m)} />" for m in members)
            mem = f"<members>{ms}</members>"
        self.extra[caption] = mem
        return name

    def ref(self, caption: str) -> str:
        return f"[Parameters].{self.cols[caption].name}"

    def column_xml(self, caption: str) -> str:
        c = self.cols[caption]
        dom = "list" if self.extra[caption] else "any"
        val = c.formula
        fmt = f" default-format={q(c.default_format)}" if c.default_format else ""
        return (f"<column caption={q(c.caption)} datatype={q(c.datatype)}{fmt} name={q(c.name)} param-domain-type={q(dom)} "
                f"role='measure' type={q(c.type)} value={q(val)}><calculation class='tableau' formula={q(val)} />"
                f"{self.extra[caption]}</column>")

    def xml(self) -> str:
        cols = "".join(self.column_xml(k) for k in self.cols)
        return f"<datasource hasconnection='false' inline='true' name='Parameters' version='18.1'><aliases enabled='yes' />{cols}</datasource>"


class Datasource:
    def __init__(self, wb: "Workbook", caption: str, directory: str, filename: str, columns: list[Column]):
        self.wb, self.caption, self.directory, self.filename = wb, caption, directory, filename
        self.name = "federated." + _id("ds", caption)
        self.conn = "textscan." + _id("conn", caption)
        self.table = filename.replace(".csv", "")
        self.base = {c.name: c for c in columns}
        self.calcs: dict[str, Column] = {}       # caption -> Column
        self.ds_filters: list[tuple[str, list]] = []   # (base column, values) data-source filters
        self.color_maps: dict[str, dict] = {}           # instance name -> {value: hex}
        self.color_insts: dict[str, str] = {}           # instance name -> column-instance xml (required at source level)

    # ---- calculated fields -------------------------------------------------
    def calc(self, caption: str, formula: str, datatype: str, fmt: str | None = None, role: str | None = None) -> str:
        n = f"[Calculation_{_id('calc', self.caption, caption, n=12)}]"   # schema requires bracketed names
        is_agg = bool(AGG_FUNCS.search(re.sub(r"\{\s*(FIXED|INCLUDE|EXCLUDE)[^}]*\}", "LOD", formula, flags=re.I))) or any(
            k in self.calcs and self.calcs[k].is_aggregate for k in re.findall(r"\{\{(.+?)\}\}", formula))
        if role is None:
            role = "measure" if (is_agg or datatype in ("real", "integer")) else "dimension"
        typ = "quantitative" if datatype in ("real", "integer") else "nominal"
        if role == "dimension" and datatype in ("real", "integer", "date", "datetime"):
            typ = "ordinal"
        self.calcs[caption] = Column(n, datatype, role, typ, caption=caption, formula=formula, default_format=fmt,
                                     is_aggregate=is_agg)
        return caption

    def _resolve(self, formula: str) -> str:
        def rep(m):
            key = m.group(1)
            if key in self.calcs:
                return self.calcs[key].name
            if key in self.wb.params.cols:
                return self.wb.params.ref(key)
            raise KeyError(f"unknown reference {{{{{key}}}}} in {self.caption}")
        return re.sub(r"\{\{(.+?)\}\}", rep, formula)

    def column(self, name: str) -> Column:
        if name in self.calcs:
            return self.calcs[name]
        key = name if name.startswith("[") else f"[{name}]"
        if key in self.base:
            return self.base[key]
        raise KeyError(f"{name} not in datasource {self.caption}")

    # ---- instance naming -----------------------------------------------------
    def instance(self, f: F) -> tuple[str, str]:
        """Returns (instance-name-without-ds, column-instance xml)."""
        c = self.column(f.name)
        raw = c.name.strip("[]")
        if c.is_aggregate:
            suf = "qk" if c.datatype in ("real", "integer") else "nk"
            deriv, prefix = "User", "usr"
            typ = "quantitative" if suf == "qk" else "nominal"
        elif f.agg:
            deriv, suf = AGG[f.agg]
            prefix = f.agg
            typ = {"qk": "quantitative", "ok": "ordinal", "nk": "nominal"}[suf]
        else:
            suf = f.kind or {"quantitative": "qk", "ordinal": "ok", "nominal": "nk"}[c.type]
            if c.role == "measure" and not f.kind:
                suf = "qk"
            deriv, prefix = "None", "none"
            typ = {"qk": "quantitative", "ok": "ordinal", "nk": "nominal"}[suf]
        inst = f"[{prefix}:{raw}:{suf}]"
        return inst, f"<column-instance column={q(c.name)} derivation={q(deriv)} name={q(inst)} pivot='key' type={q(typ)} />"

    def ref(self, f: F) -> str:
        return f"[{self.name}].{self.instance(f)[0]}"

    def column_decl(self, c: Column) -> str:
        cap = f" caption={q(c.caption)}" if c.caption else ""
        if c.semantic_role:
            cap += f" semantic-role={q(c.semantic_role)}"
        fmt = f" default-format={q(c.default_format)}" if c.default_format else ""
        body = f"<calculation class='tableau' formula={q(self._resolve(c.formula))} />" if c.formula else ""
        if body:
            return f"<column{cap} datatype={q(c.datatype)}{fmt} name={q(c.name)} role={q(c.role)} type={q(c.type)}>{body}</column>"
        return f"<column{cap} datatype={q(c.datatype)}{fmt} name={q(c.name)} role={q(c.role)} type={q(c.type)} />"

    def xml(self) -> str:
        rel_cols = "".join(f"<column datatype={q(c.datatype)} name={q(c.name.strip('[]'))} ordinal={q(i)} />"
                           for i, c in enumerate(self.base.values()))
        relation = (f"<relation connection={q(self.conn)} name={q(self.filename)} table={q('[' + self.table + '#csv]')} type='table'>"
                    f"<columns character-set='UTF-8' header='yes' locale='en_US' separator=',' text-qualifier='&quot;'>{rel_cols}</columns></relation>")
        conn = (f"<connection class='federated'><named-connections><named-connection caption={q(self.table)} name={q(self.conn)}>"
                f"<connection class='textscan' directory={q(self.directory)} filename={q(self.filename)} password='' server='' />"
                f"</named-connection></named-connections>{relation}</connection>")
        cols = "".join(self.column_decl(c) for c in list(self.base.values()) + list(self.calcs.values()))
        # Tableau Public only opens workbooks whose sources are extracts. The .hyper does not exist yet;
        # Tableau rebuilds it from the text connection on open (verified in 2026.3).
        hyper = f"{self.wb.extract_dir}/{re.sub(r'[^A-Za-z0-9_]+', '_', self.caption)}.hyper"
        extract = (f"<extract count='-1' enabled='true' units='records'>"
                   f"<connection access_mode='readonly' class='hyper' dbname={q(hyper)} default-settings='hyper' schema='Extract' "
                   f"sslmode='' tablename='Extract' username='tableau_internal_user'>"
                   f"<relation name='Extract' table='[Extract].[Extract]' type='table' /></connection></extract>")
        style = ""
        if self.color_maps:
            rules = ""
            for inst, m in self.color_maps.items():
                maps = "".join(f"<map to={q(h.lower())}><bucket>{escape(_bucket(v))}</bucket></map>" for v, h in m.items())
                rules += f"<encoding attr='color' field={q(inst)} type='palette'>{maps}</encoding>"
            style = f"<style><style-rule element='mark'>{rules}</style-rule></style>"
        sem = ""
        if any(c.semantic_role for c in self.base.values()):
            sem = "<semantic-values><semantic-value key='[Country].[Name]' value='&quot;Brasil&quot;' /></semantic-values>"
        filt = ""
        for col, vals in self.ds_filters:
            mems = "".join(f"<groupfilter function='member' level={q('[' + col + ']')} member={q(_bucket(v))} />" for v in vals)
            if len(vals) > 1:
                mems = f"<groupfilter function='union' user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate'>{mems}</groupfilter>"
            else:
                mems = mems.replace(" />", " user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate' />")
            filt += f"<filter class='categorical' column={q('[' + col + ']')} filter-group='2'>{mems}</filter>"
        return (f"<datasource caption={q(self.caption)} inline='true' name={q(self.name)} version='18.1'>{conn}"
                f"<aliases enabled='yes' />{cols}{''.join(self.color_insts.values())}{extract}"
                f"{style}{sem}{filt}</datasource>")


@dataclass
class Sheet:
    name: str
    ds: Datasource
    rows: list = field(default_factory=list)
    cols: list = field(default_factory=list)
    mark: str = "Automatic"
    color: F | None = None
    color_map: dict | None = None          # value -> hex
    mark_color: str | None = None
    text: list = field(default_factory=list)
    tooltip: list = field(default_factory=list)
    detail: list = field(default_factory=list)
    filters: list = field(default_factory=list)   # (F, [values]) categorical  |  (F, None) = keep true
    sort: tuple | None = None               # (dimension F, measure F, 'DESC'|'ASC')
    title: str | None = None
    label: str | None = None                # customized label text, may contain <field refs>
    labels: bool = False
    measure_values: list | None = None      # list of F measures shown through Measure Values
    tooltip_text: str | None = None         # sentence with {i} placeholders -> tooltip[i]
    size: F | None = None
    geo: F | None = None                    # filled map on this geographic field
    shape_mark_color: dict | None = None
    bg: str = "#FFFFFF"
    color_seq: tuple | None = None          # (low hex, high hex) for a continuous colour field
    mark_size: float | None = None
    reflines: list = field(default_factory=list)   # constant values on the first rows measure
    topn: tuple | None = None               # (dimension F, n, expression with {{refs}})
    axis_titles: dict = field(default_factory=dict)   # {F: "title"}; "" hides the title
    axis_range: tuple | None = None         # (rows measure F, min, max) fixed axis
    row_labels: bool | None = None          # show row field labels (default: only for text tables)
    font_size: int = 10
    tooltip_year: bool = False              # ATTR(year) on the tooltip, so a click can set a year parameter without splitting marks
    fmt_note: str | None = None


class Workbook:
    def __init__(self, title: str):
        self.title = title
        self.params = Parameters()
        self.datasources: list[Datasource] = []
        self.sheets: list[Sheet] = []
        self.dashboards: list[dict] = []
        self.actions: list[dict] = []
        self.palettes: dict[str, tuple] = {}
        self.hide_sheets = True          # only dashboards appear as tabs (worksheets stay reachable from the dashboards)
        self.extract_dir = "C:/Users/steph/AppData/Local/Temp/claude/2969279fcb9c72d1/bcca2772-7244-432c-82bb-04d37b4c745f/scratchpad/hyper"

    def datasource(self, caption, directory, filename, columns) -> Datasource:
        ds = Datasource(self, caption, directory, filename, columns)
        self.datasources.append(ds)
        return ds

    def sheet(self, **kw) -> Sheet:
        s = Sheet(**kw)
        self.sheets.append(s)
        return s

    def dashboard(self, name: str, width: int, height: int, zones: list[dict], background: str):
        self.dashboards.append({"name": name, "w": width, "h": height, "zones": zones, "bg": background})

    def param_action(self, caption, dashboard, sheets, field, ds, param, clear=None):
        """Click a mark in `sheets` -> set `param` from `field`; deselecting sets it back to `clear` (a string member)."""
        self.actions.append({"kind": "param", "caption": caption, "dashboard": dashboard, "sheets": sheets,
                             "field": ds.ref(field), "param": self.params.ref(param), "clear": clear})

    def filter_action(self, caption, dashboard, sources, targets):
        self.actions.append({"kind": "filter", "caption": caption, "dashboard": dashboard, "sources": sources, "targets": targets})

    def _dash_sheets(self, name):
        d = next(d for d in self.dashboards if d["name"] == name)
        return [z["sheet"] for z in d["zones"] if z["type"] == "sheet"]

    def _actions_xml(self) -> str:
        out = []
        for i, a in enumerate(self.actions, 1):
            allsheets = self._dash_sheets(a["dashboard"])
            nm = f"[Action{i}_{_id('act', self.title, a['caption'], n=32).upper()}]"
            if a["kind"] == "param":
                clr = ("<clear-option type='do-nothing' value='s:LROOT:' />" if a["clear"] is None
                       else f"<clear-option type='assign-fixed-value' value={q('s:LROOT:' + str(a['clear']))} />")
                excl = "".join(f"<exclude-sheet name={q(x)} />" for x in allsheets if x not in a["sheets"])
                out.append(f"<edit-parameter-action caption={q(a['caption'])} name={q(nm)}><activation type='on-select' />"
                           f"<source dashboard={q(a['dashboard'])} type='sheet'>{excl}</source><agg-type type='attr' />"
                           f"{clr}<params><param name='source-field' value={q(a['field'])} />"
                           f"<param name='target-parameter' value={q(a['param'])} /></params></edit-parameter-action>")
            else:
                excl = "".join(f"<exclude-sheet name={q(x)} />" for x in allsheets if x not in a["sources"])
                tex = ",".join(x for x in allsheets if x not in a["targets"])
                out.append(f"<action caption={q(a['caption'])} name={q(nm)}><activation auto-clear='true' type='on-select' />"
                           f"<source dashboard={q(a['dashboard'])} type='sheet'>{excl}</source><command command='tsc:tsl-filter'>"
                           f"<param name='exclude' value={q(tex)} /><param name='special-fields' value='all' />"
                           f"<param name='target' value={q(a['dashboard'])} /></command></action>")
        out.sort(key=lambda x: 0 if x.startswith("<action ") else 1)   # schema: action* before edit-parameter-action*
        return f"<actions>{''.join(out)}</actions>" if out else ""

    # ---- rich text -------------------------------------------------------------
    def rich(self, ds, spec, tooltip: bool = False) -> str:
        """spec: list of runs {text | field: F | br: True, size, color, bold, font}, or a plain string."""
        if isinstance(spec, str):
            spec = [{"text": spec}]
        out = []
        for r in spec:
            if r.get("br"):
                out.append("<run>\u00c6&#10;</run>")
                continue
            is_field = "field" in r
            attrs = []
            if r.get("bold") or (tooltip and is_field):
                attrs.append("bold='true'")
            default_col = "#101714" if (is_field or not tooltip) else "#454C48"
            attrs.append(f"fontcolor={q(r.get('color', default_col))}")
            attrs.append(f"fontname={q(r.get('font', 'Arial'))}")
            attrs.append(f"fontsize={q(r.get('size', 9 if tooltip else 10))}")
            body = escape(f"<{ds.ref(r['field'])}>") if is_field else escape(r["text"])
            out.append(f"<run {' '.join(attrs)}>{body}</run>")
        return "".join(out)

    # ---- worksheet xml ---------------------------------------------------------
    def _sheet_xml(self, s: Sheet) -> str:
        ds = s.ds
        # dimensions that only appear on the tooltip must be ATTR() (a bare dimension there is invalid)
        shelf = {ds.ref(f) for f in [*s.rows, *s.cols, *s.detail, *s.text] if f.name not in ("Multiple Values", ":Measure Names")}
        for f in (s.color, s.geo):
            if f:
                shelf.add(ds.ref(f))

        def fix(f):
            if f.name in ("Multiple Values", ":Measure Names") or f.agg:
                return f
            c = ds.column(f.name)
            if c.role == "dimension" and not c.is_aggregate and ds.ref(f) not in shelf:
                return F(f.name, "attr")
            return f
        s.tooltip = [fix(f) for f in s.tooltip]
        if s.tooltip_year and all(ds.ref(f) != ds.ref(F("year", "attr")) for f in s.tooltip):
            s.tooltip.append(F("year", "attr"))
        if isinstance(s.tooltip_text, list):
            s.tooltip_text = [dict(r, field=fix(r["field"])) if "field" in r else r for r in s.tooltip_text]
            for r in s.tooltip_text:
                if "field" in r and ds.ref(r["field"]) not in shelf and all(ds.ref(r["field"]) != ds.ref(t) for t in s.tooltip):
                    s.tooltip.append(r["field"])
        used: list[F] = [*s.rows, *s.cols, *s.text, *s.tooltip, *s.detail]
        if s.size:
            used.append(s.size)
        if s.geo:
            used.append(s.geo)
        if s.color:
            used.append(s.color)
        used += [flt[0] for flt in s.filters]
        if s.sort:
            used += [s.sort[0], s.sort[1]]
        if s.measure_values:
            used += s.measure_values
        insts, decls, seen_cols = {}, [], set()
        params_used = set()

        def collect(c: Column):
            if c.name in seen_cols:
                return
            seen_cols.add(c.name)
            if c.formula:
                for key in re.findall(r"\{\{(.+?)\}\}", c.formula):
                    if key in ds.calcs:
                        collect(ds.calcs[key])
                    elif key in self.params.cols:
                        params_used.add(key)
                for base in re.findall(r"\[([A-Za-z_][A-Za-z0-9_]*)\]", c.formula):
                    if f"[{base}]" in ds.base:
                        collect(ds.base[f"[{base}]"])
            decls.append(ds.column_decl(c))

        for f in used:
            if f.name in (":Measure Names", "Multiple Values"):
                continue
            c = ds.column(f.name)
            collect(c)
            n, x = ds.instance(f)
            insts[n] = x
        if s.topn:
            f0, _, expr = s.topn
            n, x = ds.instance(f0)
            insts[n] = x
            collect(ds.column(f0.name))
            for key in re.findall(r"\{\{(.+?)\}\}", expr):
                if key in ds.calcs:
                    collect(ds.calcs[key])
                elif key in self.params.cols:
                    params_used.add(key)
            for base in re.findall(r"\[([A-Za-z_][A-Za-z0-9_]*)\]", expr):
                if f"[{base}]" in ds.base:
                    collect(ds.base[f"[{base}]"])
        dep = "".join(decls) + "".join(insts.values())
        pdep = ""
        if params_used:
            pdep = ("<datasource-dependencies datasource='Parameters'>" +
                    "".join(self.params.column_xml(k) for k in sorted(params_used)) + "</datasource-dependencies>")
        dsl = f"<datasource caption={q(ds.caption)} name={q(ds.name)} />" + \
              ("<datasource caption='Parameters' name='Parameters' />" if params_used else "")

        filt, slices = "", []
        for f, values in s.filters:
            r = ds.ref(f)
            lvl = ds.instance(f)[0]
            if values is None:
                values = ["true"]
            mems = []
            for v in values:
                mv = v if (isinstance(v, (int, float)) or v in ("true", "false")) else f'"{v}"'
                mems.append(f"<groupfilter function='member' level={q(lvl)} member={q(mv)} />")
            if len(mems) == 1:
                inner = mems[0].replace("/>", "user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate' />")
            else:
                inner = f"<groupfilter function='union' user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate'>{''.join(mems)}</groupfilter>"
            filt += f"<filter class='categorical' column={q(r)}>{inner}</filter>"
            slices.append(r)
        mv_filter = ""
        if s.measure_values:
            mems = "".join(f"<groupfilter function='member' level='[:Measure Names]' member={q(chr(34) + ds.ref(m) + chr(34))} />"
                           for m in s.measure_values)
            mv_filter = (f"<filter class='categorical' column={q('[' + ds.name + '].[:Measure Names]')}>"
                         f"<groupfilter function='union' user:op='manual'>{mems}</groupfilter></filter>")
            slices.append(f"[{ds.name}].[:Measure Names]")
        if s.topn:
            f, n, expr = s.topn
            lvl = ds.instance(f)[0]
            filt += (f"<filter class='categorical' column={q(ds.ref(f))}><groupfilter count={q(n)} end='top' function='end' units='records' "
                     f"user:ui-marker='end' user:ui-top-by-field='true'><groupfilter direction='DESC' expression={q(ds._resolve(expr))} "
                     f"function='order' user:ui-marker='order'><groupfilter function='level-members' level={q(lvl)} "
                     f"user:ui-enumeration='all' user:ui-marker='enumerate' /></groupfilter></groupfilter></filter>")
            slices.append(ds.ref(f))
        sort = ""
        if s.sort:
            sort = f"<sort class='computed' column={q(ds.ref(s.sort[0]))} direction={q(s.sort[2])} using={q(ds.ref(s.sort[1]))} />"
        slices_xml = f"<slices>{''.join(f'<column>{escape(x)}</column>' for x in slices)}</slices>" if slices else ""
        msrc = "<mapsources><mapsource name='Tableau' /></mapsources>" if s.geo else ""
        view = (f"<view><datasources>{dsl}</datasources>{msrc}{pdep}<datasource-dependencies datasource={q(ds.name)}>{dep}</datasource-dependencies>"
                f"{mv_filter}{filt}{sort}{slices_xml}<aggregation value='true' /></view>")

        enc = []
        if s.color:
            enc.append(f"<color column={q(ds.ref(s.color))} />")
        elif s.measure_values and s.mark != "Text":
            enc.append(f"<color column={q('[' + ds.name + '].[:Measure Names]')} />")
        for f in s.text:
            if f.name == "Multiple Values":
                enc.append(f"<text column={q('[' + ds.name + '].[Multiple Values]')} />")
            else:
                enc.append(f"<text column={q(ds.ref(f))} />")
        for f in s.detail:
            enc.append(f"<lod column={q(ds.ref(f))} />")
        if s.geo:
            enc.append(f"<lod column={q(ds.ref(s.geo))} />")
        if s.size:
            enc.append(f"<size column={q(ds.ref(s.size))} />")
        on_shelf = {ds.ref(f) for f in [*s.rows, *s.cols, *s.text, *s.detail] if f.name not in ("Multiple Values", ":Measure Names")}
        if s.color:
            on_shelf.add(ds.ref(s.color))
        for f in s.tooltip:
            if ds.ref(f) not in on_shelf:
                enc.append(f"<tooltip column={q(ds.ref(f))} />")
                on_shelf.add(ds.ref(f))
        enc_xml = f"<encodings>{''.join(enc)}</encodings>" if enc else ""
        label = ""
        if s.label:
            label = f"<customized-label><formatted-text>{self.rich(ds, s.label)}</formatted-text></customized-label>"
        if s.tooltip_text is not None:
            label = f"<customized-tooltip><formatted-text>{self.rich(ds, s.tooltip_text, tooltip=True)}</formatted-text></customized-tooltip>" + label
        mstyle = []
        if s.mark_color:
            mstyle.append(f"<format attr='mark-color' value={q(s.mark_color)} />")
        if s.mark_size:
            mstyle.append(f"<format attr='size' value={q(s.mark_size)} />")
        mstyle.append(f"<format attr='mark-labels-show' value={q('true' if (s.labels or s.mark == 'Text') else 'false')} />")
        pstyle = f"<style><style-rule element='mark'>{''.join(mstyle)}</style-rule></style>"
        refl = ""
        for i, v in enumerate(s.reflines):
            axis = ds.ref(s.rows[0])
            refl += (f"<reference-line axis-column={q(axis)} enable-instant-analytics='true' formula='constant' id={q('refline' + str(i))} "
                     f"label-type='automatic' scope='per-table' value={q(float(v))} value-column={q(axis)} z-order='1' />")
        pane = (f"<pane selection-relaxation-option='selection-relaxation-allow'><view><breakdown value='auto' /></view>"
                f"<mark class={q(s.mark)} />{enc_xml}{refl}{label}{pstyle}</pane>")

        tstyle = [f"<style-rule element='table'><format attr='background-color' value={q(s.bg)} /></style-rule>",
                  "<style-rule element='gridline'><format attr='stroke-color' scope='rows' value='#E8E9E5' /></style-rule>"]
        if s.color and s.color_seq:
            pname = "SA – Sequential sage-forest" if len(self.palettes) == 0 or "SA – Sequential sage-forest" in self.palettes else "SA – Sequential " + "-".join(s.color_seq)
            self.palettes[pname] = s.color_seq
            tstyle.insert(0, f"<style-rule element='mark'><encoding attr='color' field={q(ds.ref(s.color))} palette={q(pname)} "
                          f"type='interpolated' /></style-rule>")
        if s.color and s.color_map:
            inst, inst_xml = ds.instance(s.color)
            ds.color_maps.setdefault(inst, {}).update(s.color_map)
            ds.color_insts[inst] = inst_xml
        if s.measure_values and s.color_map:
            mn = ds.color_maps.setdefault("[:Measure Names]", {})
            for k, v in s.color_map.items():
                mn[f"[{ds.name}].{ds.instance(F(k, 'sum') if k in ds.base or '[' + k + ']' in ds.base else F(k))[0]}"] = v
        if s.geo:
            tstyle.append("<style-rule element='map'><format attr='washout' value='0.0' /></style-rule>")
        if s.mark == "Text" and not (s.rows or s.cols):
            tstyle.append("<style-rule element='cell'><format attr='text-align' value='left' /></style-rule>")

        # readability: no field-label headers ("year", "period_date"), no date-axis titles, larger fonts
        ax = []
        for f in s.cols:
            if f.agg in ("tmn", "tyr"):
                ax.append(f"<format attr='title' class='0' field={q(ds.ref(f))} scope='cols' value='' />")
        for shelf_, sc in ((s.rows, "rows"), (s.cols, "cols")):
            if s.measure_values and any(f.name == "Multiple Values" for f in shelf_):
                ax.append(f"<format attr='title' class='0' field={q('[' + ds.name + '].[Multiple Values]')} scope={q(sc)} value='' />")
        for f, t in s.axis_titles.items():
            sc = "cols" if any(ds.ref(f) == ds.ref(c) for c in s.cols) else "rows"
            ax.append(f"<format attr='title' class='0' field={q(ds.ref(f))} scope={q(sc)} value={q(t)} />")
        if s.axis_range:
            f, lo, hi = s.axis_range
            ax.append(f"<encoding attr='space' class='0' field={q(ds.ref(f))} field-type='quantitative' max={q(hi)} min={q(lo)} "
                      f"range-type='fixed' scope='rows' type='space' />")
        if ax:
            tstyle.insert(0, f"<style-rule element='axis'>{''.join(ax)}</style-rule>")
        show_rows = s.row_labels if s.row_labels is not None else (s.mark == "Text")
        ws = [f"<format attr='font-size' value={q(s.font_size)} />", "<format attr='display-field-labels' scope='cols' value='false' />"]
        if not show_rows:
            ws.append("<format attr='display-field-labels' scope='rows' value='false' />")
        tstyle.append(f"<style-rule element='worksheet'>{''.join(ws)}</style-rule>")

        def shelf(items):
            if not items:
                return ""
            parts = []
            for f in items:
                if f.name == "Multiple Values":
                    parts.append(f"[{ds.name}].[Multiple Values]")
                elif f.name == ":Measure Names":
                    parts.append(f"[{ds.name}].[:Measure Names]")
                else:
                    parts.append(ds.ref(f))
            return escape(" / ".join(parts)) if len(parts) > 1 else escape(parts[0])

        title = ""
        if s.title:
            title = (f"<layout-options><title><formatted-text><run bold='true' fontcolor='#101714' fontname='Arial' fontsize='11'>"
                     f"{escape(s.title)}</run></formatted-text></title></layout-options>")
        rows_x, cols_x = shelf(s.rows), shelf(s.cols)
        if s.geo:
            rows_x, cols_x = escape(f"[{ds.name}].[Latitude (generated)]"), escape(f"[{ds.name}].[Longitude (generated)]")
        table = (f"<table>{view}<style>{''.join(tstyle)}</style><panes>{pane}</panes>"
                 f"<rows>{rows_x}</rows><cols>{cols_x}</cols></table>")
        return f"<worksheet name={q(s.name)}>{title}{table}<simple-id uuid={q(_uuid('ws', self.title, s.name))} /></worksheet>"

    # ---- dashboard xml -------------------------------------------------------------
    def _dash_xml(self, d: dict) -> str:
        W, H = d["w"], d["h"]
        zid = 3
        zones = []
        for z in d["zones"]:
            x, y, w, h = (round(z["x"] / W * 100000), round(z["y"] / H * 100000),
                          round(z["w"] / W * 100000), round(z["h"] / H * 100000))
            style = ""
            fmts = []
            if z.get("bg"):
                fmts.append(f"<format attr='background-color' value={q(z['bg'])} />")
            if z.get("border", True) and z.get("type") != "text-plain":
                fmts += ["<format attr='border-color' value='#D6D8D2' />", "<format attr='border-style' value='solid' />",
                         "<format attr='border-width' value='1' />"]
            fmts.append(f"<format attr='margin' value={q(z.get('margin', 4))} />")
            style = f"<zone-style>{''.join(fmts)}</zone-style>"
            common = f"h={q(h)} id={q(zid)} w={q(w)} x={q(x)} y={q(y)}"
            if z["type"] == "sheet":
                st = "" if z.get("title", True) else " show-title='false'"
                zones.append(f"<zone {common} name={q(z['sheet'])}{st}>{style}</zone>")
            elif z["type"] in ("text", "text-plain"):
                runs = "".join(
                    f"<run bold={q('true' if r.get('bold') else 'false')} fontcolor={q(r.get('color', '#101714'))} "
                    f"fontname={q(r.get('font', 'Arial'))} fontsize={q(r.get('size', 10))}>{escape(r['text'])}</run>"
                    + ("<run>\u00c6&#10;</run>" if r.get("br") else "")
                    for r in z["runs"])
                zones.append(f"<zone {common} type-v2='text'><formatted-text>{runs}</formatted-text>{style}</zone>")
            elif z["type"] == "param":
                st = "" if z.get("title", True) else " show-title='false'"
                zones.append(f"<zone {common} mode='compact' param={q(self.params.ref(z['param']))}{st} type-v2='paramctrl'>{style}</zone>")
            elif z["type"] == "nav":
                win = _uuid('wind', self.title, z["target"])
                act = escape(f'tabdoc:goto-sheet window-id="{win}"', {'"': "&quot;"})
                zones.append(f"<zone {common} type-v2='dashboard-object'><button action='{act}' button-type='text'><button-visual-state>"
                             f"<caption>{escape(z['caption'])}</caption><button-caption-font-style fontcolor={q(z.get('fg', '#f5f4ec'))} "
                             f"fontname='Arial' fontsize='8' /><format attr='background-color' value={q(z.get('bg', '#2f6b5b'))} />"
                             f"</button-visual-state></button></zone>")
            elif z["type"] == "blank":
                zones.append(f"<zone {common} type-v2='empty'>{style}</zone>")
            zid += 1
        root = "<zone h='100000' id='2' type-v2='layout-basic' w='100000' x='0' y='0' />"
        return (f"<dashboard name={q(d['name'])}><style><style-rule element='table'><format attr='background-color' value={q(d['bg'])} />"
                f"</style-rule></style><size maxheight={q(H)} maxwidth={q(W)} minheight={q(H)} minwidth={q(W)} sizing-mode='fixed' />"
                f"<zones>{root}{''.join(zones)}</zones><simple-id uuid={q(_uuid('db', self.title, d['name']))} /></dashboard>")

    def xml(self) -> str:
        cards_ws = ("<cards><edge name='left'><strip size='160'><card type='pages' /><card type='filters' /><card type='marks' /></strip></edge>"
                    "<edge name='top'><strip size='2147483647'><card type='columns' /></strip><strip size='2147483647'><card type='rows' /></strip>"
                    "<strip size='31'><card type='title' /></strip></edge></cards>")
        # worksheet windows stay visible: a dashboard zone pointing at a hidden worksheet window fails to load
        hid = " hidden='true'" if self.hide_sheets else ""
        windows = "".join(f"<window class='worksheet'{hid} name={q(s.name)}>{cards_ws}<simple-id uuid={q(_uuid('win', self.title, s.name))} /></window>"
                          for s in self.sheets)
        # schema (2026.3): dashboard window = (viewpoints, active, device-preview, simple-id)
        def vps(d):
            names = []
            for z in d["zones"]:
                if z["type"] == "sheet" and z["sheet"] not in names:
                    names.append(z["sheet"])
            return "<viewpoints>" + "".join(f"<viewpoint name={q(n)}><zoom type='entire-view' /></viewpoint>" for n in names) + "</viewpoints>"
        windows += "".join(f"<window class='dashboard' maximized='true' name={q(d['name'])}>{vps(d)}<active id='-1' />"
                           f"<simple-id uuid={q(_uuid('wind', self.title, d['name']))} /></window>"
                           for d in self.dashboards)
        ws_xml = "".join(self._sheet_xml(s) for s in self.sheets)   # first: sheets register colour maps on sources
        ds_xml = (self.params.xml() if self.params.cols else "") + "".join(ds.xml() for ds in self.datasources)
        return ("<?xml version='1.0' encoding='utf-8' ?>\n"
                "<workbook original-version='18.1' source-build='2026.3.0 (20263.26.1022.1645)' source-platform='win' version='18.1' "
                "xmlns:user='http://www.tableausoftware.com/xml/user'>"
                "<document-format-change-manifest><BasicButtonObject /><BasicButtonObjectTextSupport /><ParameterAction /><ParameterActionClearSelection /><SheetIdentifierTracking /><WindowsPersistSimpleIdentifiers /></document-format-change-manifest>"
                "<preferences><preference name='ui.encoding.shelf.height' value='24' /><preference name='ui.shelf.height' value='26' />"
                + "".join(f"<color-palette custom='true' name={q(n)} type='ordered-sequential'>" + "".join(f"<color>{c.lower()}</color>" for c in cs)
                          + "</color-palette>" for n, cs in self.palettes.items()) + "</preferences>"
                "<style><style-rule element='all'><format attr='font-family' value='Arial' /></style-rule></style>"
                f"<datasources>{ds_xml}</datasources>"
                + ("<mapsources><mapsource name='Tableau' /></mapsources>" if any(x.geo for x in self.sheets) else "")
                + 
                f"{self._actions_xml()}<worksheets>{ws_xml}</worksheets>"
                f"<dashboards>{''.join(self._dash_xml(d) for d in self.dashboards)}</dashboards>"
                f"<windows source-height='31'>{windows}</windows></workbook>\n")

    def save(self, path) -> None:
        import xml.dom.minidom
        raw = self.xml()
        xml.dom.minidom.parseString(raw.encode("utf-8"))      # well-formedness check only
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(raw)


def columns_from_dictionary(dict_csv: str, table: str, overrides: dict | None = None) -> list[Column]:
    """Build typed columns for one table from the project's tableau/data_dictionary.csv."""
    import csv
    overrides = overrides or {}
    out = []
    with open(dict_csv, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["table"] != table:
                continue
            t, n = r["tableau_type"], r["column"]
            if n in overrides:
                dt, role, typ = overrides[n]
            elif t == "String":
                dt, role, typ = "string", "dimension", "nominal"
            elif t == "Boolean":
                dt, role, typ = "boolean", "dimension", "nominal"
            elif t == "Date":
                dt, role, typ = "date", "dimension", "ordinal"
            elif t == "Number (whole)":
                dt, role, typ = "integer", "measure", "quantitative"
            else:
                dt, role, typ = "real", "measure", "quantitative"
            out.append(Column(f"[{n}]", dt, role, typ))
    if not out:
        raise ValueError(f"table {table} not in dictionary")
    return out
