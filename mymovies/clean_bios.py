import psycopg2


def clean_biography(biography):
    if not biography:
        return None

    cut_phrases = [
        "Description above from the Wikipedia article",
        "licensed under CC-BY-SA",
        "Full list of contributors on Wikipedia",
        "full list of contributors on Wikipedia",
    ]

    cleaned = biography
    for phrase in cut_phrases:
        if phrase in cleaned:
            cleaned = cleaned.split(phrase)[0].strip()

    return cleaned.strip() if cleaned else None


def clean_bios():
    conn = psycopg2.connect(dbname="django", host="/tmp")
    cur = conn.cursor()

    try:
        cur.execute("SELECT id, biography FROM movies_person WHERE biography IS NOT NULL")
        rows = cur.fetchall()

        updated = 0
        for person_id, biography in rows:
            cleaned = clean_biography(biography)
            if cleaned != biography:
                cur.execute(
                    "UPDATE movies_person SET biography = %s WHERE id = %s",
                    (cleaned, person_id)
                )
                updated += 1

        conn.commit()
        print(f"✅ Biografías limpiadas: {updated}")

    except Exception as e:
        conn.rollback()
        print("❌ Error:", e)
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    clean_bios()
