from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta, datetime
import os

# ---------------- CONFIGURAÇÃO ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "carregamentos.db")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "chave_super_segura_trocar_aqui"
app.permanent_session_lifetime = timedelta(minutes=60)

db = SQLAlchemy(app)

# ---------------- STATUS DISPONÍVEIS ----------------
STATUS_OPTIONS = [
    "Não chegou para coletar",
    "Em coleta",
    "Finalizado a coleta"
]

# ---------------- MODELOS ----------------
class Funcionario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo_funcional = db.Column(db.String(50), unique=True, nullable=False)
    senha_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)

class Carregamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    placa = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    rota = db.Column(db.String(100), nullable=True)
    destino = db.Column(db.String(200), nullable=True)
    entrega_finalizada = db.Column(db.Boolean, default=False)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ---------------- FUNÇÃO DE SEED ----------------
def criar_seed():
    """Cria dados iniciais no banco se ainda não existirem"""
    if not Funcionario.query.filter_by(codigo_funcional="125039").first():
        admin = Funcionario(codigo_funcional="125039")
        admin.set_password("125039")
        db.session.add(admin)

    if Carregamento.query.count() == 0:
        exemplos = [
            Carregamento(placa="ABC1A23", status="Não chegou para coletar", rota="Rota A", destino="Cliente X"),
            Carregamento(placa="DEF2B34", status="Em coleta", rota="Rota B", destino="Cliente Y"),
            Carregamento(placa="GHI3C45", status="Finalizado a coleta", rota="Rota C", destino="Cliente Z", entrega_finalizada=True),
        ]
        db.session.bulk_save_objects(exemplos)
    db.session.commit()

# ---------------- ROTAS ----------------

@app.route("/")
def home():
    """Página inicial redireciona conforme login"""
    if "funcionario" in session:
        return redirect(url_for("index"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    """Tela e processo de login"""
    if "funcionario" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        codigo = request.form.get("codigo")
        senha = request.form.get("senha")

        if not codigo or not senha:
            flash("Preencha código funcional e senha.", "warning")
            return render_template("login.html")

        funcionario = Funcionario.query.filter_by(codigo_funcional=codigo).first()
        if funcionario and funcionario.check_password(senha):
            session["funcionario"] = funcionario.codigo_funcional
            session.permanent = True
            flash(f"Bem-vindo(a), {funcionario.codigo_funcional}!", "success")
            return redirect(url_for("index"))
        else:
            flash("Código funcional ou senha incorretos.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    """Encerrar sessão"""
    session.clear()
    flash("Você foi desconectado com sucesso.", "info")
    return redirect(url_for("login"))

@app.route("/index")
def index():
    """Tabela principal de acompanhamento"""
    if "funcionario" not in session:
        return redirect(url_for("login"))

    carregamentos = Carregamento.query.order_by(Carregamento.atualizado_em.desc()).all()
    return render_template("index.html", carregamentos=carregamentos, funcionario=session["funcionario"])

@app.route("/adicionar", methods=["GET", "POST"])
def adicionar():
    """Adicionar novo carregamento"""
    if "funcionario" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        placa = request.form.get("placa", "").strip()
        status = request.form.get("status", STATUS_OPTIONS[0])
        rota = request.form.get("rota", "").strip()
        destino = request.form.get("destino", "").strip()
        entrega_finalizada = request.form.get("entrega_finalizada") == "on"

        if not placa:
            flash("Placa é obrigatória.", "warning")
            return render_template("adicionar.html", status_options=STATUS_OPTIONS)

        novo = Carregamento(
            placa=placa,
            status=status,
            rota=rota,
            destino=destino,
            entrega_finalizada=entrega_finalizada
        )
        db.session.add(novo)
        db.session.commit()
        flash("Carregamento adicionado com sucesso!", "success")
        return redirect(url_for("index"))

    return render_template("adicionar.html", status_options=STATUS_OPTIONS)

@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    """Editar carregamento existente"""
    if "funcionario" not in session:
        return redirect(url_for("login"))

    carregamento = Carregamento.query.get_or_404(id)
    if request.method == "POST":
        carregamento.placa = request.form.get("placa", carregamento.placa).strip()
        carregamento.status = request.form.get("status", carregamento.status)
        carregamento.rota = request.form.get("rota", carregamento.rota).strip()
        carregamento.destino = request.form.get("destino", carregamento.destino).strip()
        carregamento.entrega_finalizada = request.form.get("entrega_finalizada") == "on"

        db.session.commit()
        flash("Carregamento atualizado com sucesso!", "success")
        return redirect(url_for("index"))

    return render_template("editar.html", carregamento=carregamento, status_options=STATUS_OPTIONS)

@app.route("/excluir/<int:id>", methods=["POST"])
def excluir(id):
    """Excluir carregamento"""
    if "funcionario" not in session:
        return redirect(url_for("login"))

    carregamento = Carregamento.query.get_or_404(id)
    db.session.delete(carregamento)
    db.session.commit()
    flash("Carregamento excluído com sucesso!", "info")
    return redirect(url_for("index"))

# ---------------- INICIALIZAÇÃO ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        criar_seed()
    app.run(debug=True)
