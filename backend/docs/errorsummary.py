# -*- coding: utf-8 -*-

import os
import re
import sys
import inspect
import bottle

from docutils.parsers.rst import directives
from docutils.statemachine import ViewList
from docutils import nodes

from sphinx import addnodes
from sphinx.util.compat import Directive
from sphinx.ext.autodoc import DocstringSignatureMixin, ClassLevelDocumenter

from utils.i18n import translate

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
    pass


def autosummary_noop(self, node):
    pass


# -- autosummary_table node ----------------------------------------------------

class autosummary_table(nodes.comment):
    pass


def autosummary_table_visit_html(self, node):
    """Make the first column of the table non-breaking."""
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


# -- .. errorsummary:: ----------------------------------------------------------

class ErrorSummary(Directive):
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
        errors = []
        for name in modules:
            try:
                real_name, obj, parent = import_by_name(name, prefixes=prefixes)
                for i in inspect.getmembers(obj):
                    if not i[0].startswith('__') and i[0] != '_':  # _ is for gettext
                        errors.append(i)
            except ImportError:
                continue

            for e in errors:
                error_type = e[1]
                if not hasattr(error_type, "default_status"):
                    continue
                message = error_type.message if not error_type in [bottle.HTTPError, BaseException] else ''
                error_code = error_type.default_status

                display_name = '`{}`'.format(error_type.__name__)
                documenter = get_documenter(None, parent)(self, display_name)

                # -- Grab the signature
                sig = documenter.format_signature()
                if not sig:
                    sig = ''
                else:
                    max_chars = max(10, max_item_chars - len(display_name))
                    sig = mangle_signature(sig, max_chars=max_chars)
                    sig = sig.replace('*', r'\*')

                # -- Grab the summary

                doc = list(documenter.process_doc(documenter.get_doc()))

                while doc and not doc[0].strip():
                    doc.pop(0)
                summary = ''
                if message:
                    summary = message

                items.setdefault(error_type.__name__, []).append((display_name, sig, summary, "view." + display_name,
                                                                  error_code))

        return items

    def get_table(self, items_set):
        """Generate a proper list of table nodes for errorsummary:: directive.

        *items* is a list produced by :meth:`get_items`.
        """
        table_spec = addnodes.tabular_col_spec()
        table_spec['spec'] = 'll'

        table = autosummary_table('')
        real_table = nodes.table('', classes=['longtable'])
        table.append(real_table)
        group = nodes.tgroup('', cols=3)
        real_table.append(group)
        group.append(nodes.colspec('', colwidth=70))
        group.append(nodes.colspec('', colwidth=20))
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

        col1 = u"**Name**"
        col2 = u"**Code**"
        col3 = u"**Message**"
        append_row(col1, col2, col3)

        for class_name, items in sorted(items_set.items()):
            for name, sig, summary, real_name, code in items:
                if 'nosignatures' not in self.options:
                    col1 = '_%s' % name
                col2 = '{}'.format(code)
                translated = translate(summary, "ru") if summary else ""
                if translated != summary:
                    col3 = u"{} / {}".format(translated, summary)
                else:
                    col3 = summary

                append_row(col1, col2, col3)

        return [table_spec, table]


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


def import_by_name(name, prefixes=None):
    """Import a Python object that has the given *name*, under one of the
    *prefixes*.  The first name that succeeds is used.
    """
    prefixes = prefixes or [None]
    tried = []
    for prefix in prefixes:
        if prefix:
            prefixed_name = '.'.join([prefix, name])
        else:
            prefixed_name = name
        try:
            obj, parent = _import_by_name(prefixed_name)
            return prefixed_name, obj, parent
        except ImportError:
            tried.append(prefixed_name)
    raise ImportError('no module named %s' % ' or '.join(tried))


def _import_by_name(name):
    """Import a Python object given its full name."""
    try:
        name_parts = name.split('.')

        # try first interpret `name` as MODNAME.OBJ
        modname = '.'.join(name_parts[:-1])
        if modname:
            try:
                __import__(modname)
                mod = sys.modules[modname]
                return getattr(mod, name_parts[-1]), mod
            except (ImportError, IndexError, AttributeError):
                pass

        # ... then as MODNAME, MODNAME.OBJ1, MODNAME.OBJ1.OBJ2, ...
        last_j = 0
        modname = None
        for j in reversed(range(1, len(name_parts)+1)):
            last_j = j
            modname = '.'.join(name_parts[:j])
            try:
                __import__(modname)
            except ImportError:
                continue
            if modname in sys.modules:
                break

        if last_j < len(name_parts):
            parent = None
            obj = sys.modules[modname]
            for obj_name in name_parts[last_j:]:
                parent = obj
                obj = getattr(obj, obj_name)
            return obj, parent
        else:
            return sys.modules[modname], None
    except (ValueError, ImportError, AttributeError, KeyError) as  e:
        raise ImportError(*e.args)


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
    app.add_directive('errorsummary', ErrorSummary)
    app.add_role('autolink', autolink_role)
    app.connect('doctree-read', process_autosummary_toc)
    app.connect('builder-inited', process_generate_options)
    # app.add_config_value('autosummary_generate', [], True)
    #

    # app.add_autodocumenter(ApiDocumenter)
