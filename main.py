# VERSÃO DEFINITIVA PARA GOOGLE CLOUD RUN

import os
import random
import gspread
import json
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# --- Configuração do Google Sheets ---
# COLE O CONTEÚDO DO SEU ARQUIVO credentials.json AQUI DENTRO DAS ASPAS TRIPLAS
google_credentials_str = """
{
  "type": "service_account",
  "project_id": "seu-id-de-projeto-aqui",
  "private_key_id": "sua-key-id-aqui",
  "private_key": "-----BEGIN PRIVATE KEY-----\\nSUA-CHAVE-PRIVADA-AQUI\\n-----END PRIVATE KEY-----\\n",
  "client_email": "seu-email-de-servico@iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x500_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
"""
google_credentials_dict = json.loads(google_credentials_str)

try:
    gc = gspread.service_account_from_dict(google_credentials_dict)
    spreadsheet = gc.open("Denuncias_Chatbot")
    worksheet = spreadsheet.get_worksheet(0)
except Exception as e:
    print(f"Erro ao conectar com Google Sheets: {e}")
    worksheet = None
# ------------------------------------

LOJAS_DE_RISCO = ["loja do zé", "importados duvidosos", "xyz eletronicos"]

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)
    
    try:
        intent_name = req['queryResult']['intent']['displayName']
        
        # Lógica para quando a coleta de dados da intent 'iniciar_denuncia' termina
        if intent_name == 'iniciar_denuncia':
            all_params_present = req['queryResult'].get('allRequiredParamsPresent', False)
            if all_params_present:
                return jsonify({
                    "followupEventInput": {
                        "name": "evt_confirmar_denuncia",
                        "languageCode": "pt-BR"
                    }
                })
            else:
                # Durante a coleta de dados, não faz nada, apenas retorna uma resposta vazia.
                return jsonify({})

        # Lógica para quando o usuário confirma o envio
        elif intent_name == 'confirmar_envio - yes': 
            params = req['queryResult']['parameters']
            
            prioridade = "Normal"
            motivo_risco = params.get('motivo', '').lower()
            tem_nf = params.get('nf', '').lower()
            loja = params.get('loja', '').lower()

            if "vazamento" in motivo_risco and tem_nf == "não" and loja in LOJAS_DE_RISCO:
                prioridade = "Alta"

            protocolo = f"DEN-{random.randint(10000, 99999)}"
            
            if worksheet:
                nova_linha = [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    protocolo,
                    prioridade,
                    params.get('produto'),
                    params.get('modelo'),
                    params.get('serie'),
                    params.get('canal'),
                    params.get('loja'),
                    params.get('data', {}).get('date_time', '').split('T')[0],
                    params.get('local_uf'),
                    params.get('local_mun'),
                    str(params.get('valor', {}).get('amount', 'N/A')),
                    params.get('nf'),
                    params.get('motivo')
                ]
                worksheet.append_row(nova_linha)

            resposta_texto = (f"Denúncia registrada com sucesso! ✅\n"
                              f"Seu número de protocolo é: {protocolo}.\n"
                              f"A prioridade foi definida como: {prioridade}.\n"
                              "Nossa equipe de análise entrará em contato se precisar de mais informações.")

            return jsonify({"fulfillmentText": resposta_texto})

    except Exception as e:
        print(f"Erro no webhook: {e}")
        return jsonify({"fulfillmentText": "Ocorreu um erro no meu sistema. Por favor, tente novamente."})

    # Resposta padrão caso nenhuma intent seja reconhecida pela lógica do webhook
    return jsonify({})

# Esta parte do código permite testar o servidor localmente, mas não é usada pelo Cloud Run.
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)