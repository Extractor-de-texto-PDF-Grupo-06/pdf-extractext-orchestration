import http from 'k6/http';
import { check } from 'k6';

export const options = {
    stages: [
        { duration: '10s', target: 100 },
        { duration: '20s', target: 100 },
        { duration: '10s', target: 0 },
    ],
};

const BASE_URL = __ENV.BASE_URL || 'http://traefik:8081';

const pdfFiles = [
    open('/load/pdfs/2020-Scrum-Guide-Spanish-Latin-South-American.pdf', 'b'),
    open('/load/pdfs/Essential-Kanban-Condensed-Spanish.pdf', 'b'),
    open('/load/pdfs/Filosofia Lean.pdf', 'b'),
    open('/load/pdfs/scrum_manager_historias_usuario.pdf', 'b'),
];

export default function () {
    const pdf = pdfFiles[Math.floor(Math.random() * pdfFiles.length)];
    const res = http.post(`${BASE_URL}/extract`, pdf, {
        headers: { 'Content-Type': 'application/pdf' },
    });
    check(res, { 'status 200': (r) => r.status === 200 });
}
