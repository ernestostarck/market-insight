import React from 'react';
import { BarChart3, BookOpen, GitCompare, Sparkles } from 'lucide-react';

interface SuggestedQuestionsProps {
  onSelectQuestion: (question: string) => void;
}

interface QuestionCategory {
  title: string;
  icon: React.ReactNode;
  questions: string[];
}

const CATEGORIES: QuestionCategory[] = [
  {
    title: 'Consultas Cuantitativas (SQL)',
    icon: <BarChart3 className="h-4 w-4 text-blue-500" />,
    questions: [
      '¿Cuáles fueron los 5 mayores compradores de salud en 2024?',
      '¿Cuánto dinero se adjudicó por trato directo en los últimos 6 meses?',
      '¿Qué proveedores ganaron más licitaciones en la Región Metropolitana?',
    ],
  },
  {
    title: 'Análisis Documental & Pliegos (RAG)',
    icon: <BookOpen className="h-4 w-4 text-emerald-500" />,
    questions: [
      '¿Qué requisitos técnicos exigen para licitaciones de ambulancias?',
      '¿Cuáles son las cláusulas de garantía más comunes en compras TI?',
      '¿Existe alguna licitación activa para adquisición de camas clínicas?',
    ],
  },
  {
    title: 'Inteligencia Híbrida de Mercado',
    icon: <GitCompare className="h-4 w-4 text-purple-500" />,
    questions: [
      'Compara los precios unitarios de mascarillas N95 entre organismos públicos.',
      'Analiza la concentración de proveedores en servicios de seguridad privada.',
    ],
  },
];

export const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({ onSelectQuestion }) => {
  return (
    <div className="w-full max-w-3xl mx-auto space-y-4 py-6">
      <div className="text-center space-y-1">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold">
          <Sparkles className="h-3.5 w-3.5" />
          Asistente de Compras Públicas ChileCompra
        </div>
        <h2 className="text-lg font-bold text-foreground">
          ¿En qué puedo ayudarte hoy?
        </h2>
        <p className="text-xs text-muted-foreground">
          Selecciona una pregunta de inicio rápido o escribe tu propia consulta cuantitativa o documental.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {CATEGORIES.map((cat, idx) => (
          <div
            key={idx}
            className="rounded-xl border border-border/70 bg-card/60 p-3.5 space-y-2.5 backdrop-blur-sm"
          >
            <div className="flex items-center gap-2 font-semibold text-xs text-foreground">
              {cat.icon}
              {cat.title}
            </div>
            <div className="space-y-1.5">
              {cat.questions.map((q, qIdx) => (
                <button
                  key={qIdx}
                  onClick={() => onSelectQuestion(q)}
                  className="w-full text-left p-2 rounded-lg text-xs text-muted-foreground hover:text-foreground bg-muted/30 hover:bg-muted/70 transition-all border border-transparent hover:border-border leading-relaxed"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
