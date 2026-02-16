"use client";

const sources = [
    "Bloomberg", "Alpha Vantage", "SEC Edgar", "News APIs", "Yahoo Finance"
];

export default function DataSources() {
    return (
        <section className="section-padding px-8 bg-black/40 border-t border-white/5">
            <div className="max-w-7xl mx-auto text-center">
                <h2 className="text-3xl font-bold mb-16 tracking-tight gradient-text">Powered by Multiple Data Sources</h2>

                <div className="flex flex-wrap justify-center items-center gap-12 md:gap-24 opacity-40 grayscale hover:grayscale-0 transition-all duration-1000 ease-in-out">
                    {sources.map(source => (
                        <div key={source} className="text-2xl font-black tracking-tighter hover:text-white transition-colors cursor-default select-none">
                            {source.toUpperCase()}
                        </div>
                    ))}
                </div>

                <p className="mt-20 text-sm text-gray-500 max-w-2xl mx-auto leading-relaxed">
                    Aggregates fundamental data, estimates, price action, and sentiment from industry-leading
                    providers to ensure your analysis is built on a solid foundation.
                </p>
            </div>
        </section>
    );
}
