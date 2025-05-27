import os, sys, subprocess, textwrap
from pathlib import Path

# ────────────────────────────────────────────────────────────────
# CONFIG
# ----------------------------------------------------------------
ROOT = Path(__file__).parent.resolve()
ENV_NAME  = "myEnv"
PY_BIN    = sys.executable
ENV_BIN   = ROOT / ENV_NAME / ("Scripts" if os.name == "nt" else "bin")
PIP       = ENV_BIN / ("pip.exe" if os.name == "nt" else "pip")
PY        = ENV_BIN / ("python.exe" if os.name == "nt" else "python")

REQ_FILE  = ROOT / "requirements.txt"
DEFAULT_REQS = textwrap.dedent("""\
    Flask>=3.0.0
    Flask-Login>=0.6.3
    Flask-WTF>=1.2.1
    Flask-Migrate>=4.0.7
    SQLAlchemy>=2.0.29
    bcrypt>=4.1.2
    python-dotenv>=1.0.1
    itsdangerous>=2.1.2
    openai>=1.25.0
    pytest>=8.1.1
    Faker>=25.0.0
""").strip() + "\n"

# ────────────────────────────────────────────────────────────────
# FILE & FOLDER PAYLOADS
# ----------------------------------------------------------------
FILES: dict[str, str] = {

    # ───── app core ─────
    "app/__init__.py": textwrap.dedent("""\
        from flask import Flask
        from .config      import Config
        from .extensions  import db, migrate, login_manager
        from .auth.routes import auth_bp
        from .main.routes import main_bp

        def create_app(config_class=Config):
            app = Flask(__name__, instance_relative_config=False)
            app.config.from_object(config_class)

            db.init_app(app)
            migrate.init_app(app, db)
            login_manager.init_app(app)

            app.register_blueprint(auth_bp)
            app.register_blueprint(main_bp)

            return app
    """),

    "app/config.py": textwrap.dedent("""\
        import os
        from pathlib import Path
        BASE_DIR = Path(__file__).resolve().parent.parent

        class Config:
            SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
            SQLALCHEMY_DATABASE_URI = os.getenv(
                "DATABASE_URL",
                f"sqlite:///{BASE_DIR/'instance'/'mindforge.db'}"
            )
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    """),

    "app/extensions.py": textwrap.dedent("""\
        from flask_sqlalchemy  import SQLAlchemy
        from flask_login       import LoginManager
        from flask_migrate     import Migrate

        db            = SQLAlchemy()
        migrate       = Migrate()
        login_manager = LoginManager()
        login_manager.login_view = 'auth_bp.login'
    """),

    # ───── models ─────
    "app/models/__init__.py": "",
    "app/models/user.py": textwrap.dedent("""\
        import uuid
        from datetime import datetime
        from flask_login      import UserMixin
        from werkzeug.security import generate_password_hash, check_password_hash
        from ..extensions     import db, login_manager

        class User(UserMixin, db.Model):
            id       = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
            name     = db.Column(db.String(120), nullable=False)
            email    = db.Column(db.String(120), unique=True, nullable=False)
            password = db.Column(db.String(128), nullable=False)
            created  = db.Column(db.DateTime, default=datetime.utcnow)

            def set_password(self, raw): self.password = generate_password_hash(raw)
            def verify_password(self, raw): return check_password_hash(self.password, raw)

        @login_manager.user_loader
        def load_user(uid): return User.query.get(uid)
    """),

    "app/models/goal.py": textwrap.dedent("""\
        from datetime import datetime
        from ..extensions import db

        class Goal(db.Model):
            id        = db.Column(db.Integer, primary_key=True)
            user_id   = db.Column(db.String(36), db.ForeignKey('user.id'))
            horizon   = db.Column(db.String(10))  # '1m', '1y', '10y'
            text      = db.Column(db.String(255))
            created   = db.Column(db.DateTime, default=datetime.utcnow)
    """),

    # ───── services ─────
    "app/services/__init__.py": "",
    "app/services/ai_service.py": textwrap.dedent("""\
        import functools, openai, os
        openai.api_key = os.getenv("OPENAI_API_KEY", "")

        def _ask(prompt, max_tokens=120):
            resp = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}],
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip()

        def memoize(func):
            cache = {}
            @functools.wraps(func)
            def inner(*a, **k):
                key = (func.__name__,) + a + tuple(k.items())
                if key not in cache: cache[key] = func(*a, **k)
                return cache[key]
            return inner

        @memoize
        def bio(name, age, occupation, goal):
            prompt = f"Write a 2-line bio for {name}, {age}, a {occupation}. Short-term goal: {goal}"
            return _ask(prompt, 60)
    """),

    # ───── auth blueprint ─────
    "app/auth/__init__.py": "",
    "app/auth/forms.py": textwrap.dedent("""\
        from flask_wtf import FlaskForm
        from wtforms    import StringField, PasswordField, SubmitField
        from wtforms.validators import DataRequired, Email, Length, EqualTo

        class SignupForm(FlaskForm):
            name     = StringField('Name',  validators=[DataRequired(), Length(1,120)])
            email    = StringField('Email', validators=[DataRequired(), Email(), Length(1,120)])
            password = PasswordField('Password', validators=[DataRequired(), Length(8,128)])
            confirm  = PasswordField('Confirm', validators=[EqualTo('password')])
            submit   = SubmitField('Sign Up')

        class LoginForm(FlaskForm):
            email    = StringField('Email', validators=[DataRequired(), Email()])
            password = PasswordField('Password', validators=[DataRequired()])
            submit   = SubmitField('Log In')
    """),

    "app/auth/routes.py": textwrap.dedent("""\
        from flask import Blueprint, render_template, redirect, url_for, flash
        from flask_login import login_user, logout_user, login_required
        from ..extensions import db
        from ..models.user import User
        from .forms       import SignupForm, LoginForm

        auth_bp = Blueprint('auth_bp', __name__, template_folder='templates')

        @auth_bp.route('/signup', methods=['GET','POST'])
        def signup():
            form = SignupForm()
            if form.validate_on_submit():
                if User.query.filter_by(email=form.email.data.strip().lower()).first():
                    flash('Email already exists', 'error')
                else:
                    user = User(
                        name=form.name.data.strip(),
                        email=form.email.data.strip().lower())
                    user.set_password(form.password.data)
                    db.session.add(user); db.session.commit()
                    login_user(user); return redirect(url_for('main_bp.home'))
            return render_template('public/signup.html', form=form)

        @auth_bp.route('/login', methods=['GET','POST'])
        def login():
            form = LoginForm()
            if form.validate_on_submit():
                user = User.query.filter_by(email=form.email.data.strip().lower()).first()
                if user and user.verify_password(form.password.data):
                    login_user(user); return redirect(url_for('main_bp.home'))
                flash('Invalid credentials', 'error')
            return render_template('public/login.html', form=form)

        @auth_bp.route('/logout')
        @login_required
        def logout():
            logout_user(); return redirect(url_for('auth_bp.login'))
    """),

    # ───── main blueprint ─────
    "app/main/__init__.py": "",
    "app/main/forms.py": "# future goal-edit forms\n",
    "app/main/routes.py": textwrap.dedent("""\
        from flask import Blueprint, render_template
        from flask_login import login_required, current_user
        from ..services.ai_service import bio

        main_bp = Blueprint('main_bp', __name__, template_folder='templates')

        @main_bp.route('/home')
        @login_required
        def home():
            sample_goal = 'Finish my outline'
            my_bio = bio(current_user.name, 30, 'Developer', sample_goal)
            return render_template('private/home.html',
                                   user=current_user, bio=my_bio)
    """),

    # ───── templates ─────
    "app/templates/base.html": textwrap.dedent("""\
        <!doctype html><html lang="en">
        <head>
          <meta charset="utf-8" />
          <title>{% block title %}MindForge{% endblock %}</title>
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <script src="https://cdn.tailwindcss.com?plugins=typography"></script>
        </head>
        <body class="min-h-screen bg-slate-100 flex flex-col">
          {% with msgs = get_flashed_messages(with_categories=true) %}
          {% if msgs %}
            <ul class="p-4">{% for c,m in msgs %}
              <li class="text-sm {{'text-red-600' if c=='error' else 'text-green-600'}}">{{ m }}</li>
            {% endfor %}</ul>
          {% endif %}{% endwith %}
          {% block content %}{% endblock %}
        </body></html>
    """),

    "app/templates/public/signup.html": textwrap.dedent("""\
        {% extends 'base.html' %}{% block title %}Sign Up{% endblock %}
        {% block content %}
        <div class="max-w-md mx-auto my-10 bg-white p-6 rounded shadow">
          <h2 class="text-2xl font-bold mb-4">Create Account</h2>
          <form method="post">
            {{ form.hidden_tag() }}
            {{ form.name.label }} {{ form.name(class="w-full mb-3") }}
            {{ form.email.label }} {{ form.email(class="w-full mb-3") }}
            {{ form.password.label }} {{ form.password(class="w-full mb-3") }}
            {{ form.confirm.label }} {{ form.confirm(class="w-full mb-3") }}
            {{ form.submit(class="bg-blue-600 text-white px-4 py-2 rounded") }}
          </form>
          <p class="mt-4 text-sm">Have an account?
            <a href="{{ url_for('auth_bp.login') }}" class="text-blue-600">Log in</a></p>
        </div>{% endblock %}
    """),

    "app/templates/public/login.html": textwrap.dedent("""\
        {% extends 'base.html' %}{% block title %}Log In{% endblock %}
        {% block content %}
        <div class="max-w-md mx-auto my-10 bg-white p-6 rounded shadow">
          <h2 class="text-2xl font-bold mb-4">Welcome Back</h2>
          <form method="post">
            {{ form.hidden_tag() }}
            {{ form.email.label }} {{ form.email(class="w-full mb-3") }}
            {{ form.password.label }} {{ form.password(class="w-full mb-3") }}
            {{ form.submit(class="bg-blue-600 text-white px-4 py-2 rounded") }}
          </form>
          <p class="mt-4 text-sm">Need an account?
            <a href="{{ url_for('auth_bp.signup') }}" class="text-blue-600">Sign up</a></p>
        </div>{% endblock %}
    """),

    "app/templates/private/home.html": textwrap.dedent("""\
        {% extends 'base.html' %}{% block title %}Dashboard{% endblock %}
        {% block content %}
        <div class="flex flex-col lg:flex-row">
          <aside class="lg:w-1/3 p-6 bg-gray-50">
            <h3 class="text-xl font-semibold mb-4">You Now</h3>
            <p><strong>Name:</strong> {{ user.name }}</p>
            <p><strong>Email:</strong> {{ user.email }}</p>
            <p class="mt-4 italic">{{ bio }}</p>
          </aside>
          <section class="lg:w-2/3 p-6">
            <h3 class="text-xl font-semibold mb-4">Thoughts → Future You</h3>
            <p class="text-gray-600">AI-generated resources coming soon…</p>
          </section>
        </div>{% endblock %}
    """),

    "app/templates/components/_flash.html": "<!-- flash msg macro placeholder -->\n",

    # ───── static ─────
    "app/static/css/main.css": "/* Tailwind builds will overwrite this if desired */\n",
    "app/static/js/main.js":   "// Alpine/HTMX sprinkles here\n",
    "app/static/images/.gitkeep": "",

    # ───── migrations & alembic placeholder ─────
    "migrations/README": "Initialize with `flask db init`.\n",

    # ───── tests ─────
    "tests/conftest.py": textwrap.dedent("""\
        import pytest, os
        from app import create_app, extensions

        @pytest.fixture
        def app():
            os.environ['FLASK_ENV'] = 'testing'
            _app = create_app()
            _app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
            with _app.app_context():
                extensions.db.create_all()
                yield _app
    """),
    "tests/test_auth.py": "def test_placeholder(): assert True\n",
    "tests/test_main.py": "def test_placeholder(): assert True\n",

    # ───── dev tools ─────
    "dev_tools/seed_data.py": textwrap.dedent("""\
        \"\"\"Seed local DB with fake users & goals.\"\"\"
        from faker import Faker
        from app import create_app, extensions
        fake = Faker()
        app  = create_app()
        with app.app_context():
            extensions.db.create_all()
            print('Seed complete (placeholder)')
    """),

    # ───── docs ─────
    "docs/architecture.md": "# MindForge – Architecture\n\n_TODO: diagram_",
    "docs/API.md": "# API Endpoints\n\n_TODO_",
    "docs/prompt-library.md": "# Prompt Library\n\n_TODO_",
    "docs/deployment-runbook.md": "# Deployment Runbook\n\n_TODO_",

    # ───── misc top-level ─────
    ".env.example": "SECRET_KEY=change-me\nOPENAI_API_KEY=\n",
    ".gitignore": textwrap.dedent("""\
        myEnv/
        __pycache__/
        *.pyc
        instance/
        .env
    """),
    "README.md": textwrap.dedent("""\
        # MindForge

        ## Quick start
        ```bash
        python bootstrap.py
        source myEnv/bin/activate  # or myEnv\\Scripts\\activate on Windows
        flask --app run.py db upgrade
        flask --app run.py run --debug
        ```
    """),

    "run.py": textwrap.dedent("""\
        from app import create_app
        app = create_app()

        if __name__ == '__main__':
            app.run()
    """),
}

# ────────────────────────────────────────────────────────────────
# HELPERS
# ----------------------------------------------------------------
def create_files():
    for rel, content in FILES.items():
        path = ROOT / rel
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(content)
            print(f"✓  {rel}")
        else:
            print(f"•  {rel} already exists")

def ensure_requirements():
    if not REQ_FILE.exists():
        REQ_FILE.write_text(DEFAULT_REQS)
        print("✓  requirements.txt written")
    else:
        print("•  requirements.txt exists")

def create_venv():
    if not (ROOT / ENV_NAME).exists():
        subprocess.check_call([PY_BIN, "-m", "venv", ENV_NAME])
        print(f"✓  virtual-env '{ENV_NAME}' created")
    else:
        print(f"•  virtual-env '{ENV_NAME}' exists")

def pip_install():
    print("📦  installing dependencies …")
    subprocess.check_call([str(PIP), "install", "-r", str(REQ_FILE)])
    print("✓  dependencies installed")

# ────────────────────────────────────────────────────────────────
# MAIN
# ----------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 Bootstrapping MindForge\n")
    create_files()
    ensure_requirements()
    create_venv()
    pip_install()

    print("\n✅  All done!\n"
          f"Activate the env and run:\n"
          f"    source {ENV_NAME}/bin/activate  # (Windows: {ENV_NAME}\\Scripts\\activate)\n"
          f"    flask --app run.py db upgrade\n"
          f"    flask --app run.py run --debug\n")