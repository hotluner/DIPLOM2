import math
from typing import List, Dict, Optional


class MovieRecommender:

    def __init__(self, db):

        self.db = db


        self.weights = {

            "genre": 0.30,
            "actor": 0.20,
            "director": 0.15,
            "year": 0.10,
            "rating": 0.25

        }

    def get_recommendations(
            self,
            user,
            top_n: int = 25
    ) -> List[Dict]:


        movies = self.db.get_all_movies()


        if not movies:

            return []



        if (
            not user.preferences
            and not user.ratings
        ):

            return self._get_popular_movies(
                top_n
            )



        result = []


        skipped = user.skipped.keys()



        for movie in movies:



            if movie["movie_id"] in user.ratings:
                continue



            if movie["movie_id"] in skipped:
                continue



            score = self._calculate_score(
                movie,
                user,
                movies
            )



            result.append({

                **movie,

                "score":
                    round(score,4)

            })



        result.sort(

            key=lambda x:x["score"],

            reverse=True

        )



        recommendations = result[:top_n]



        if len(recommendations) < top_n:


            recommendations.extend(

                self._get_popular_movies(
                    top_n-len(recommendations)
                )

            )



        return recommendations

    def _calculate_score(
            self,
            movie,
            user,
            all_movies
    ):


        score = 0



        prefs = user.preferences



        score += (

            self._jaccard(

                movie.get("genres",[]),

                prefs.get("genres",[])

            )

            *

            self.weights["genre"]

        )



        score += (

            self._jaccard(

                movie.get("actors",[]),

                prefs.get("actors",[])

            )

            *

            self.weights["actor"]

        )



        score += (

            self._jaccard(

                movie.get("directors",[]),

                prefs.get("directors",[])

            )

            *

            self.weights["director"]

        )



        score += (

            self._year_score(

                movie.get("year"),

                prefs.get("year_from"),

                prefs.get("year_to")

            )

            *

            self.weights["year"]

        )



        similar = self._find_similar_movies(

            movie,

            all_movies

        )


        score += (

            self._rating_score(

                similar,

                user

            )

            *

            self.weights["rating"]

        )



        return score

    def _jaccard(
            self,
            a,
            b
    ):


        if not a or not b:
            return 0



        a=set(a)
        b=set(b)



        return len(a&b)/len(a|b)

    def _find_similar_movies(
            self,
            movie,
            movies,
            limit=5
    ):


        result=[]



        for other in movies:


            if (
                other["movie_id"]
                ==
                movie["movie_id"]
            ):
                continue



            similarity = self._jaccard(

                movie.get("genres",[]),

                other.get("genres",[])

            )



            if similarity > 0.2:


                result.append(

                    (
                    other,
                    similarity
                    )

                )



        result.sort(

            key=lambda x:x[1],

            reverse=True

        )



        return [

            x[0]

            for x in result[:limit]

        ]

    def _rating_score(
            self,
            movies,
            user
    ):


        ratings=[]



        for movie in movies:


            movie_id = movie["movie_id"]



            if movie_id in user.ratings:


                ratings.append(

                    user.ratings[movie_id]

                )



        if not ratings:

            return 0



        return (

            sum(ratings)

            /

            len(ratings)

        ) / 10

    def _year_score(
            self,
            year,
            year_from,
            year_to
    ):


        if not year:
            return 0



        if not year_from and not year_to:

            return 1



        if year_from:

            if year < int(year_from):

                return 0



        if year_to:

            if year > int(year_to):

                return 0



        return 1

    def _get_popular_movies(
            self,
            limit=10
    ):


        movies=self.db.get_all_movies()



        for movie in movies:


            rating = movie.get(
                "imdb_rating",
                0
            )


            movie["popularity"] = rating



        movies.sort(

            key=lambda x:x["popularity"],

            reverse=True

        )



        return movies[:limit]

