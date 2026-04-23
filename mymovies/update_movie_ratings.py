import environ
import psycopg2
import requests


def get_json(url, headers):
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def update_movie_ratings():
    env = environ.Env()
    environ.Env.read_env(".env")

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {env('API_TOKEN')}",
    }

    conn = psycopg2.connect(dbname="django", host="/tmp")
    cur = conn.cursor()

    try:
        cur.execute("SELECT id, title, tmdb_id FROM movies_movie WHERE tmdb_id IS NOT NULL")
        movies = cur.fetchall()

        updated = 0

        for movie_id, title, tmdb_id in movies:
            url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?language=en-US"

            try:
                data = get_json(url, headers)
            except Exception as e:
                print(f"Error con {title}: {e}")
                continue

            cur.execute(
                """
                UPDATE movies_movie
                SET tmdb_vote_average = %s,
                    tmdb_vote_count = %s
                WHERE id = %s
                """,
                (
                    data.get("vote_average"),
                    data.get("vote_count"),
                    movie_id,
                )
            )

            updated += 1
            print(f"Actualizada: {title}")

        conn.commit()
        print(f"\n✅ Películas actualizadas: {updated}")

    except Exception as e:
        conn.rollback()
        print("❌ Error:", e)
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    update_movie_ratings()
