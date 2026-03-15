import React, { useState, useEffect } from 'react';
import Home from './components/Home';
import QuizBoard from './components/QuizBoard';
import Result from './components/Result';

function App() {
    const [view, setView] = useState('home'); // home, quiz, result
    const [questions, setQuestions] = useState([]);
    const [currentQuestions, setCurrentQuestions] = useState([]);
    const [selectedTheme, setSelectedTheme] = useState(null);
    const [score, setScore] = useState(0);
    const [userAnswers, setUserAnswers] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('/data/questions.json')
            .then(res => res.json())
            .then(data => {
                setQuestions(data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Data loading failed:", err);
                setLoading(false);
            });
    }, []);

    const startQuiz = (theme = null, minCount = 1) => {
        let filtered = [];
        if (theme === 'wrong') {
            const saved = localStorage.getItem('wrong_attempts');
            const wrongCounts = saved ? JSON.parse(saved) : {};
            // ID 매칭을 위해 String 변환 적용 (보수적 접근)
            filtered = questions.filter(q => (wrongCounts[String(q.id)] || 0) >= minCount);
            setSelectedTheme(`wrong_${minCount}`);
        } else if (theme) {
            const ranges = {
                'fire': [0, 60],
                'inland': [60, 120],
                'package': [120, 180],
                'bi': [180, 240],
                'reinsurance': [240, 300],
                'ox': [300, 400]
            };
            const range = ranges[theme];
            if (range) {
                filtered = questions.slice(range[0], range[1]);
            }
            setSelectedTheme(theme);
        } else {
            // 랜덤 모의고사
            filtered = [...questions].sort(() => 0.5 - Math.random()).slice(0, 20);
            setSelectedTheme('mock');
        }

        if (theme === 'wrong' && filtered.length === 0) {
            alert(minCount === 1 ? "틀린 문제가 없습니다!" : `${minCount}회 이상 틀린 문제가 없습니다.`);
            return;
        }

        if (filtered.length > 0) {
            setCurrentQuestions(filtered);
            setScore(0);
            setUserAnswers([]);
            setView('quiz');
        }
    };

    const finishQuiz = (finalScore, answers) => {
        setScore(finalScore);
        setUserAnswers(answers);
        setView('result');
    };

    const retryQuiz = () => {
        setScore(0);
        setUserAnswers([]);
        setView('quiz');
    };

    const retryFailed = () => {
        const failedIds = userAnswers.filter(a => !a.isCorrect).map(a => a.qId);
        const failedQuestions = questions.filter(q => failedIds.includes(q.id));
        setCurrentQuestions(failedQuestions);
        setScore(0);
        setUserAnswers([]);
        setView('quiz');
    };

    const goHome = () => {
        setView('home');
        setSelectedTheme(null);
    };

    if (loading) return (
        <div className="app-container" style={{ justifyContent: 'center', alignItems: 'center' }}>
            <div className="fade-in">학습 데이터를 불러오는 중입니다...</div>
        </div>
    );

    return (
        <div className="app-container">
            {view === 'home' && <Home startQuiz={startQuiz} />}
            {view === 'quiz' && (
                <QuizBoard
                    questions={currentQuestions}
                    finishQuiz={finishQuiz}
                    goHome={goHome}
                    themeName={selectedTheme}
                />
            )}
            {view === 'result' && (
                <Result
                    score={score}
                    total={currentQuestions.length}
                    answers={userAnswers}
                    goHome={goHome}
                    retryQuiz={retryQuiz}
                    retryFailed={retryFailed}
                />
            )}
        </div>
    );
}

export default App;
