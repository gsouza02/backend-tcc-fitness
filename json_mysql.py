import json
import pymysql

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "port": 3306,
    "password": "root",
    "database": "TCC"
}

def save_exercicios_from_file(json_path="exercicios.json"):
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        print("❌ O arquivo precisa conter uma lista de objetos JSON.")
        return

    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    insert_query = """
        INSERT INTO exercicios (nome, equipamento, grupo_muscular)
        VALUES (%s, %s, %s)
    """

    total = len(data)
    success = 0
    failed = 0

    for i, ex in enumerate(data, start=1):
        try:
            cursor.execute(insert_query, (
                ex.get("nome"),
                ex.get("equipamento"),
                ex.get("grupo_muscular")
            ))
            success += 1
        except Exception as e:
            failed += 1
            print(f"❌ Erro no exercício {i}: {e}")

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\n✅ Inseridos com sucesso: {success}/{total}")
    print(f"⚠️ Falharam: {failed}")

if __name__ == "__main__":
    save_exercicios_from_file()
