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
    rota = db.Column(db.String(100))
    destino = db.Column(db.String(200))
    entrega_finalizada = db.Column(db.Boolean, default=False)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    atualizado_por = db.Column(db.String(50))  # coluna para registrar quem atualizou


# ---------------- SEED ----------------
def criar_seed():
    """Cria usuário e carregamentos iniciais, se ainda não existirem."""
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
    return redirect(url_for("listar_carregamentos"))


@app.route("/carregamentos")
def listar_carregamentos():
    carregamentos = Carregamento.query.order_by(Carregamento.atualizado_em.desc()).all()
    return render_template("carregamentos.html", carregamentos=carregamentos)


# ---------------- EXECUÇÃO ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        criar_seed()

    print("✅ Aplicação Flask rodando com sucesso!")
    print("🌐 Acesse: http://127.0.0.1:5000/carregamentos")
    app.run(debug=True)
