import os
import re
import sys
import inspect

from docutils.parsers.rst import directives
from docutils.statemachine import ViewList
from docutils import nodes

from sphinx import addnodes
from sphinx.util.compat import Directive
from sphinx.ext.autodoc import DocstringSignatureMixin, ClassLevelDocumenter, py_ext_sig_re
from sphinx.ext.autosummary import import_by_name

# -- autosummary_toc node ------------------------------------------------------


class autosummary_toc(nodes.comment):
    pass


def process_autosummary_toc(app, doctree):
    """Insert items described in autosummary:: to the TOC tree, but do
    not generate the toctree:: list.
    """
    env = app.builder.env
    crawled = {}

    def crawl_toc(node, depth=1):
        crawled[node] = True
        for j, subnode in enumerate(node):
            try:
                if isinstance(subnode, autosummary_toc) and isinstance(subnode[0], addnodes.toctree):
                    env.note_toctree(env.docname, subnode[0])
                    continue
            except IndexError:
                continue
            if not isinstance(subnode, nodes.section):
                continue
            if subnode not in crawled:
                crawl_toc(subnode, depth+1)
    crawl_toc(doctree)


def autosummary_toc_visit_html(self, node):
    """Hide autosummary toctree list in HTML output."""
    raise nodes.SkipNode


def autosummary_noop(self, node):
    pass


# -- autosummary_table node ----------------------------------------------------

class autosummary_table(nodes.comment):
    pass


def autosummary_table_visit_html(self, node):
    """Make the first column of the table non-breaking."""
    try:
        tbody = node[0][0][-1]
        for row in tbody:
            col1_entry = row[0]
            par = col1_entry[0]
            for j, subnode in enumerate(list(par)):
                if isinstance(subnode, nodes.Text):
                    new_text = unicode(subnode.astext())
                    new_text = new_text.replace(u" ", u"\u00a0")
                    par[j] = nodes.Text(new_text)
    except IndexError:
        pass


# -- autodoc integration -------------------------------------------------------

class FakeDirective:
    env = {}
    genopt = {}


def get_documenter(obj, parent):
    """Get an autodoc.Documenter class suitable for documenting the given
    object.

    *obj* is the Python object to be documented, and *parent* is an
    another Python object (e.g. a module or a class) to which *obj*
    belongs to.
    """
    from sphinx.ext.autodoc import AutoDirective, DataDocumenter, ModuleDocumenter

    if inspect.ismodule(obj):
        # ModuleDocumenter.can_document_member always returns False
        return ModuleDocumenter

    # Construct a fake documenter for *parent*
    if parent is not None:
        parent_doc_cls = get_documenter(parent, None)
    else:
        parent_doc_cls = ModuleDocumenter

    if hasattr(parent, '__name__'):
        parent_doc = parent_doc_cls(FakeDirective(), parent.__name__)
    else:
        parent_doc = parent_doc_cls(FakeDirective(), "")

    # Get the corrent documenter class for *obj*
    classes = [cls for cls in AutoDirective._registry.values()
               if cls.can_document_member(obj, '', False, parent_doc)]
    if classes:
        classes.sort(key=lambda cls: cls.priority)
        return classes[-1]
    else:
        return DataDocumenter


# -- .. autosummary:: ----------------------------------------------------------

class APISummary(Directive):
    """
    Pretty table containing short signatures and summaries of functions etc.
    """

    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    has_content = True
    option_spec = {
        'nosignatures': directives.flag,
        'template': directives.unchanged,
    }

    def warn(self, msg):
        self.warnings.append(self.state.document.reporter.warning(
            msg, line=self.lineno))

    def run(self):
        self.env = self.state.document.settings.env
        self.genopt = {}
        self.warnings = []

        names = [x.strip().split()[0] for x in self.content
                 if x.strip() and re.search(r'^[~a-zA-Z_]', x.strip()[0])]
        items = self.get_items(names)
        nodes = self.get_table(items)

        return self.warnings + nodes

    def get_items(self, modules):
        """Try to import the given names, and return a list of
        ``[(name, signature, summary_string, real_name), ...]``.
        """
        env = self.state.document.settings.env

        prefixes = get_import_prefixes_from_env(env)

        items = {}

        max_item_chars = 80
        callbacks_already_met = set()

        for name in modules:
            try:
                real_name, obj, parent, modename = import_by_name(name, prefixes=prefixes)
            except ImportError:
                self.warn("import name failed: %s" % name)
                continue
            try:
                routes = obj().routes
            except Exception:
                continue

            for r in routes:
                callback = r.callback
                if not hasattr(callback, "_mapped_to") or callback in callbacks_already_met:
                    continue
                callbacks_already_met.add(callback)

                rule = r.rule
                method = r.method
                clas = callback.__self__.__class__.__name__
                display_name = "%s %s" % (method, rule)
                documenter = get_documenter(callback, parent)(self, display_name)
                documenter.object = callback

                # -- Grab the signature
                sig = documenter.format_signature()
                if not sig:
                    sig = ''
                else:
                    max_chars = max(10, max_item_chars - len(display_name))
                    sig = mangle_signature(sig, max_chars=max_chars)

                # -- Grab the summary

                doc = list(documenter.process_doc(documenter.get_doc()))

                while doc and not doc[0].strip():
                    doc.pop(0)
                m = re.search(r"^([A-Z][^A-Z]*?\.\s)", " ".join(doc).strip())
                if m:
                    summary = m.group(1).strip()
                elif doc:
                    summary = doc[0].strip()
                else:
                    summary = ''

                items.setdefault(clas, []).append((escape_rst(display_name), escape_rst(sig),
                                                   summary, display_name))

        return items

    def get_table(self, items_set):
        """Generate a proper list of table nodes for autosummary:: directive.

        *items* is a list produced by :meth:`get_items`.
        """
        table_spec = addnodes.tabular_col_spec()
        table_spec['spec'] = 'll'

        table = autosummary_table('')
        real_table = nodes.table('', classes=['longtable'])
        table.append(real_table)
        group = nodes.tgroup('', cols=2)
        real_table.append(group)
        group.append(nodes.colspec('', colwidth=10))
        group.append(nodes.colspec('', colwidth=90))
        body = nodes.tbody('')
        group.append(body)

        def append_row(*column_texts):
            row = nodes.row('')
            for text in column_texts:
                node = nodes.paragraph('')
                vl = ViewList()
                vl.append(text, '<autosummary>')
                self.state.nested_parse(vl, 0, node)
                try:
                    if isinstance(node[0], nodes.paragraph):
                        node = node[0]
                except IndexError:
                    pass
                row.append(nodes.entry('', node))
            body.append(row)

        for class_name, items in sorted(items_set.items()):
            append_row("**%s**" % class_name, "")
            for name, sig, summary, real_name in sorted(items):
                qualifier = 'obj'
                if 'nosignatures' not in self.options:
                    col1 = ':%s:`%s <%s>`\ %s' % (qualifier, name, real_name, sig)
                else:
                    col1 = ':%s:`%s <%s>`' % (qualifier, name, real_name)
                col2 = summary
                append_row(col1, col2)

        return [table_spec, table]


def escape_rst(s):
    return re.sub(r"([<>\*])", r"\\\1", s)


def mangle_signature(sig, max_chars=30):
    """Reformat a function signature to a more compact form."""
    s = re.sub(r"^\((.*)\)$", r"\1", sig).strip()

    # Strip strings (which can contain things that confuse the code below)
    s = re.sub(r"\\\\", "", s)
    s = re.sub(r"\\'", "", s)
    s = re.sub(r"'[^']*'", "", s)

    # Parse the signature to arguments + options
    args = []
    opts = []

    opt_re = re.compile(r"^(.*, |)([a-zA-Z0-9_*]+)=")
    while s:
        m = opt_re.search(s)
        if not m:
            # The rest are arguments
            args = s.split(', ')
            break

        opts.insert(0, m.group(2))
        s = m.group(1)[:-2]

    # Produce a more compact signature
    sig = limited_join(", ", args, max_chars=max_chars-2)
    if opts:
        if not sig:
            sig = "[%s]" % limited_join(", ", opts, max_chars=max_chars-4)
        elif len(sig) < max_chars - 4 - 2 - 3:
            sig += "[, %s]" % limited_join(", ", opts,
                                           max_chars=max_chars-len(sig)-4-2)

    return u"(%s)" % sig


def limited_join(sep, items, max_chars=30, overflow_marker="..."):
    """Join a number of strings to one, limiting the length to *max_chars*.

    If the string overflows this limit, replace the last fitting item by
    *overflow_marker*.

    Returns: joined_string
    """
    full_str = sep.join(items)
    if len(full_str) < max_chars:
        return full_str

    n_chars = 0
    n_items = 0
    for j, item in enumerate(items):
        n_chars += len(item) + len(sep)
        if n_chars < max_chars - len(overflow_marker):
            n_items += 1
        else:
            break

    return sep.join(list(items[:n_items]) + [overflow_marker])

# -- Importing items -----------------------------------------------------------


def get_import_prefixes_from_env(env):
    """
    Obtain current Python import prefixes (for `import_by_name`)
    from ``document.env``
    """
    prefixes = [None]

    currmodule = env.temp_data.get('py:module')
    if currmodule:
        prefixes.insert(0, currmodule)

    currclass = env.temp_data.get('py:class')
    if currclass:
        if currmodule:
            prefixes.insert(0, currmodule + "." + currclass)
        else:
            prefixes.insert(0, currclass)

    return prefixes


# -- :autolink: (smart default role) -------------------------------------------

def autolink_role(typ, rawtext, etext, lineno, inliner,
                  options=None, content=None):
    """Smart linking role.

    Expands to ':obj:`text`' if `text` is an object that can be imported;
    otherwise expands to '*text*'.
    """
    options = options or {}
    content = content or []
    env = inliner.document.settings.env
    r = env.get_domain('py').role('obj')(
        'obj', rawtext, etext, lineno, inliner, options, content)
    pnode = r[0][0]

    prefixes = get_import_prefixes_from_env(env)
    try:
        import_by_name(pnode['reftarget'], prefixes)
    except ImportError:
        content = pnode[0]
        r[0][0] = nodes.emphasis(rawtext, content[0].astext(),
                                 classes=content['classes'])
    return r


def process_generate_options(app):
    genfiles = app.config.autosummary_generate

    ext = app.config.source_suffix

    if genfiles and not hasattr(genfiles, '__len__'):
        env = app.builder.env
        genfiles = [x + ext for x in env.found_docs
                    if os.path.isfile(env.doc2path(x))]

    if not genfiles:
        return

    from sphinx.ext.autosummary.generate import generate_autosummary_docs

    genfiles = [genfile + (not genfile.endswith(ext) and ext or '')
                for genfile in genfiles]

    generate_autosummary_docs(genfiles, builder=app.builder,
                              warn=app.warn, info=app.info, suffix=ext,
                              base_path=app.srcdir)


class ApiDocumenter(DocstringSignatureMixin, ClassLevelDocumenter):
    """
    Specialized Documenter subclass for methods (normal, static and class).
    """
    objtype = 'method'
    member_order = 50
    priority = 0

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return inspect.isroutine(member) and hasattr(member, '_method')

    def format_args(self):
        doc = self.object.__doc__
        if not doc:
            return None
        r = re.compile(":param\s+(\w+\s)*(\w+):")
        matches = r.findall(doc)
        sig = [m[1] for m in matches]
        return "%s" % (", ".join(sig), )

    def document_members(self, all_members=False):
        pass


def setup(app):
    # I need autodoc
    app.setup_extension('sphinx.ext.autodoc')
    app.add_node(autosummary_toc,
                 html=(autosummary_toc_visit_html, autosummary_noop),
                 latex=(autosummary_noop, autosummary_noop),
                 text=(autosummary_noop, autosummary_noop),
                 man=(autosummary_noop, autosummary_noop),
                 texinfo=(autosummary_noop, autosummary_noop))
    app.add_node(autosummary_table,
                 html=(autosummary_table_visit_html, autosummary_noop),
                 latex=(autosummary_noop, autosummary_noop),
                 text=(autosummary_noop, autosummary_noop),
                 man=(autosummary_noop, autosummary_noop),
                 texinfo=(autosummary_noop, autosummary_noop))
    app.add_directive('apisummary', APISummary)
    app.add_role('autolink', autolink_role)
    app.connect('doctree-read', process_autosummary_toc)
    app.connect('builder-inited', process_generate_options)
    app.add_config_value('autosummary_generate', [], True)

    app.add_autodocumenter(ApiDocumenter)
