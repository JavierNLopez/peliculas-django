from django import forms


class MovieReviewForm(forms.Form):
    title = forms.CharField(
        label="Título",
        required=True,
        widget=forms.TextInput(attrs={
            "class": "block w-full rounded-md bg-white px-3 py-2 text-base text-gray-900 outline outline-1 outline-gray-300 placeholder:text-gray-400 focus:outline focus:outline-2 focus:outline-indigo-600"
        })
    )

    rating = forms.IntegerField(
        label="Calificación",
        min_value=1,
        max_value=10,
        required=True,
        widget=forms.NumberInput(attrs={
            "class": "block w-full rounded-md bg-white px-3 py-2 text-base text-gray-900 outline outline-1 outline-gray-300 placeholder:text-gray-400 focus:outline focus:outline-2 focus:outline-indigo-600"
        })
    )

    review = forms.CharField(
        label="Reseña",
        min_length=20,
        required=True,
        widget=forms.Textarea(attrs={
            "class": "block w-full rounded-md bg-white px-3 py-2 text-base text-gray-900 outline outline-1 outline-gray-300 placeholder:text-gray-400 focus:outline focus:outline-2 focus:outline-indigo-600",
            "rows": 5
        })
    )
