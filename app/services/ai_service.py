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
