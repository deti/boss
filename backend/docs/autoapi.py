import inspect
import re
from operator import attrgetter
import sphinx.ext.autodoc as autodoc
from docutils import nodes
from sphinx.domains.python import PythonDomain, PyObject, TypedField, GroupedField, l_, _
from sphinx.ext.autosummary import Autosummary, autosummary_table, ViewList, \
    get_import_prefixes_from_env, import_by_name, get_documenter, mangle_signature
from sphinx import addnodes
from sphinx.util.docstrings import prepare_docstring
from sphinx.util import force_decode


class AutoAPI(autodoc.ModuleDocumenter):
    objtype = 'api'
    priority = 11
    directivetype = 'module'
    domain = "pyapi"

    def resolve_name(self, modname, parents, path, base):
        return modname, parents + [base]

    def get_object_members(self, want_all):
        routes = self.object().routes
        ret = {}
        for r in routes:
            callback = r.callback
            rule = r.rule
            method = r.method
            try:
                clas = r.callback.__self__.__class__
            except AttributeError:
                continue  # skip functions
            else:
                ret.setdefault(clas, []).append(("%s %s" % (method, rule), callback))
        return False, ret

    def document_members(self, all_members=False):
        want_all = all_members or self.options.inherited_members or self.options.members is autodoc.ALL
        # find out which members are documentable
        members_check_module, members_set = self.get_object_members(want_all)

        resources_already_met = set()
        for clas in sorted(members_set.keys(), key=attrgetter("__name__")):
            members = members_set[clas]
            processed_members = []
            for member in members:
                if isinstance(member, (tuple, list)):
                    resource, func, rest = member[0], member[1], member[2:]
                    if hasattr(func, '_mapped_to') and resource.rstrip("/") not in resources_already_met:
                        resources_already_met.add(resource)
                        processed_members.append((resource, func) + rest)
                else:
                    processed_members.append(members)

            # document non-skipped members
            memberdocumenters = []
            for (mname, member, isattr) in self.filter_members(processed_members, want_all):
                classes = [cls for cls in autodoc.AutoDirective._registry.values()
                           if cls.can_document_member(member, mname, isattr, self)]
                if not classes:
                    # don't know how to document this member
                    continue
                    # prefer the documenter with the highest priority
                classes.sort(key=lambda cls: cls.priority)
                documenter = classes[-1](self.directive, mname, self.indent)
                memberdocumenters.append((documenter, isattr, member))
            member_order = self.options.member_order or self.env.config.autodoc_member_order
            if member_order == 'groupwise':
                # sort by group; relies on stable sort to keep items in the
                # same group sorted alphabetically
                memberdocumenters.sort(key=lambda e: e[0].member_order)
            elif member_order == 'bysource' and self.analyzer:
                # sort by source order, by virtue of the module analyzer
                tagorder = self.analyzer.tagorder

                def keyfunc(entry):
                    fullname = entry[0].name.split('::')[1]
                    return tagorder.get(fullname, len(tagorder))
                memberdocumenters.sort(key=keyfunc)
            else:
                # sort by name
                memberdocumenters.sort(key=lambda e: e[2]._mapped_to.keys())

            self.add_line(u'', '<autodoc>')
            self.add_line(clas.__name__, '<autodoc>')
            self.add_line("*" * len(clas.__name__), '<autodoc>')

            docstring = self.get_attr(clas, '__doc__', None)
            if docstring:
                if isinstance(docstring, str):
                    docstring = prepare_docstring(docstring)
                elif docstring:
                    docstring = prepare_docstring(force_decode(docstring, None))

                for s in docstring:
                    self.add_line(s, '<autodoc>')

            for documenter, isattr, member in memberdocumenters:
                documenter.object = member
                documenter.generate_api(
                    all_members=True, real_modname=self.real_modname,
                    check_module=members_check_module and not isattr)
                self.add_line("-----", '<autodoc>')


class AutoAPIMethod(autodoc.MethodDocumenter):
    objtype = 'function_api'
    directivetype = 'function'
    priority = 11
    member_order = 40
    domain = "pyapi"

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return inspect.isroutine(member) and ' ' in membername

    def format_name(self):
        # normally the name doesn't contain the module (except for module
        # directives of course)
        self.fullname = self.name
        return self.name

    def generate_api(self, more_content=None, real_modname=None, check_module=False, all_members=False):
        self.real_modname = None
        self.objpath = []

        self.analyzer = None
        # TODO added analyzer and file name

        # make sure that the result starts with an empty line.  This is
        # necessary for some situations where another directive preprocesses
        # reST and no starting newline is present
        self.add_line(u'', '<autodoc>')

        # format the object's signature, if any
        sig = self.format_signature()

        # generate the directive header and options, if applicable
        self.add_directive_header(sig)
        self.add_line(u'', '<autodoc>')

        # e.g. the module directive doesn't have content
        self.indent += self.content_indent

        # add all content (from docstrings, attribute docs etc.)
        self.add_content(more_content)

        # document members, if possible
        self.document_members(all_members)


class PythonAPIDomain(PythonDomain):
    name = "pyapi"

    def __init__(self, *arg, **kwargs):
        super(PythonAPIDomain, self).__init__(*arg, **kwargs)
        self.directives['function'] = PyAPILevel


class PyAPILevel(PyObject):

    """
    Description of an object on module level (functions, data).
    """

    def needs_arglist(self):
        return True

    def get_index_text(self, modname, name_cls):
        if not modname:
            return _('%s() (built-in function)') % name_cls[0]
        return _('%s() (in module %s)') % (name_cls[0], modname)

    doc_field_types = \
        [
            TypedField('parameter', label=l_('Parameters'),
                       names=('param', 'parameter', 'arg', 'argument',
                              'keyword', 'kwarg', 'kwparam'),
                       typerolename='obj', typenames=('paramtype', 'type'),
                       can_collapse=True),
            TypedField('variable', label=l_('Variables'), rolename='obj',
                       names=('var', 'ivar', 'cvar'),
                       typerolename='obj', typenames=('vartype',),
                       can_collapse=True),
            GroupedField('exceptions', label=l_('Raises'), rolename='exc',
                         names=('raises', 'raise', 'exception', 'except'),
                         can_collapse=True),
            TypedField('return', label=l_('Returns'),  # has_arg=False,
                       names=('returns', 'return', 'rv'), typenames=('returntype', ),
                       typerolename='obj', can_collapse=True),
            # TypedField('returntype', label=l_('Return type'), # has_arg=False,
            #             names=('rtype',)),
        ]

    def handle_signature(self, sig, signode):
        """Transform a Python signature into RST nodes.

        Return (fully qualified name of the thing, classname if any).

        If inside a class, the current class name is handled intelligently:
        * it is stripped from the displayed name if present
        * it is added to the full name (return value) if not present
        """
        # determine module and class name (if applicable), as well as full name
        from sphinx import addnodes

        r = re.compile(r"(\w+)\s+([^\(]+)\s*\((.*)\)")
        m = r.match(sig)
        if m is None:
            raise ValueError

        method, name, arglist = m.groups()

        modname = self.options.get(
            'module', self.env.temp_data.get('py:module'))
        classname = ''
        fullname = "%s %s" % (method, name)

        signode['module'] = modname
        signode['class'] = classname
        signode['fullname'] = fullname

        signode += addnodes.desc_name(fullname, fullname)

        if not arglist:
            return fullname, ''

        from sphinx.domains.python import _pseudo_parse_arglist

        _pseudo_parse_arglist(signode, arglist)
        return fullname, ''


def process_signature(app, what, name, obj, options, signature, return_annotation):
    if what != 'function_api':
        return None

    doc = obj.__doc__
    if not doc:
        return None
    r = re.compile(":param\s+(\w+\s)*(\w+):")
    matches = r.findall(doc)
    sig = [m[1] for m in matches]
    return "(%s)" % (", ".join(sig), ), ""


class ApiList(Autosummary):

    def get_table(self, items):
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

        for name, sig, summary, real_name in items:
            qualifier = 'obj'
            if 'nosignatures' not in self.options:
                col1 = ':%s:`%s <%s>`\ %s' % (qualifier, name, name, sig)
            else:
                col1 = ':%s:`%s <%s>`' % (qualifier, name, real_name)
            col2 = summary
            append_row(col1, col2)

        return [table_spec, table]

    def get_items(self, names):
        """Try to import the given names, and return a list of
        ``[(name, signature, summary_string, real_name), ...]``.
        """
        env = self.state.document.settings.env

        prefixes = get_import_prefixes_from_env(env)

        items = []

        max_item_chars = 50

        for name in names:
            display_name = name
            if name.startswith('~'):
                name = name[1:]
                display_name = name.split('.')[-1]

            try:
                real_name, obj, parent = import_by_name(name, prefixes=prefixes)
            except ImportError:
                self.warn('failed to import %s' % name)
                items.append((name, '', '', name))
                continue

            # NB. using real_name here is important, since Documenters
            #     handle module prefixes slightly differently
            documenter = get_documenter(obj, parent)(self, real_name)
            if not documenter.parse_name():
                self.warn('failed to parse name %s' % real_name)
                items.append((display_name, '', '', real_name))
                continue
            if not documenter.import_object():
                self.warn('failed to import object %s' % real_name)
                items.append((display_name, '', '', real_name))
                continue
            display_name = documenter.format_name()

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
            m = re.search(r"^([A-Z][^A-Z]*?\.\s)", " ".join(doc).strip())
            if m:
                summary = m.group(1).strip()
            elif doc:
                summary = doc[0].strip()
            else:
                summary = ''

            items.append((display_name, sig, summary, real_name))

        return items


def setup(app):
    app.add_domain(PythonAPIDomain)
    app.add_autodocumenter(AutoAPI)
    app.add_autodocumenter(AutoAPIMethod)

    app.connect('autodoc-process-signature', process_signature)

#    app.add_directive('apilist', ApiList)
