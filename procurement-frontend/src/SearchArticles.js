import React, { useState, useEffect } from "react";
import axios from "axios";

const SearchArticles = () => {
    const [query, setQuery] = useState("");
    const [articles, setArticles] = useState([]);

    const fetchArticles = async () => {
        if (query.trim() === "") return;
        try {
            const response = await axios.get(`http://127.0.0.1:8000/articles/?query=${query}`);
            setArticles(response.data);
        } catch (error) {
            console.error("Error fetching articles:", error);
        }
    };

    useEffect(() => {
        fetchArticles();
    }, [query]);

    return (
        <div>
            <h2>bitte tippen einen Artikelname ein</h2>
            <input
                type="text"
                placeholder="suchen Sie nach einem name"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
            />
            <button onClick={fetchArticles}>Search</button>
            <ul>
                {articles.map((article) => (
                    <li key={article.article_id}>
                        <strong>{article.article_name}</strong> - {article.description}
                    </li>
                ))}
            </ul>
        </div>
    );
};

export default SearchArticles;
