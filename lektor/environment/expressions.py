class Expression:
    def __init__(self, env, expr):
        self.env = env
        self.tmpl = env.jinja_env.from_string("{{ __result__(%s) }}" % expr)

    def evaluate(self, pad=None, this=None, values=None, alt=None):
        result = []

        def result_func(value):
            result.append(value)
            return ""

        values = self.env.make_default_tmpl_values(pad, this, values, alt)
        values["__result__"] = result_func
        self.tmpl.render(values)
        return result[0]


class FormatExpression:
    def __init__(self, env, expr):
        self.env = env
        self.tmpl = env.jinja_env.from_string(expr)

    def evaluate(self, pad=None, this=None, values=None, alt=None):
        values = self.env.make_default_tmpl_values(pad, this, values, alt)
        return self.tmpl.render(values)
