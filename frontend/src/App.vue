<template>
  <div id="app">
    <header class="header">
      <h1>ENEM Questions RAG System</h1>
      <nav>
        <button @click="activeTab = 'search'" :class="{ active: activeTab === 'search' }">
          Buscar
        </button>
        <button @click="activeTab = 'stats'" :class="{ active: activeTab === 'stats' }">
          Estatísticas
        </button>
      </nav>
    </header>

    <main class="main">
      <!-- Search Tab -->
      <div v-if="activeTab === 'search'" class="tab-content">
        <div class="filters">
          <select v-model="filters.year" @change="loadQuestions">
            <option value="">Todos os anos</option>
            <option v-for="year in stats.years_available" :key="year" :value="year">
              {{ year }}
            </option>
          </select>
          
          <select v-model="filters.subject" @change="loadQuestions">
            <option value="">Todas as matérias</option>
            <option v-for="subject in stats.subjects" :key="subject" :value="subject">
              {{ subject }}
            </option>
          </select>

          <input 
            type="number" 
            v-model="filters.size" 
            @change="loadQuestions"
            min="1" 
            max="100" 
            placeholder="Itens por página"
          />
        </div>

        <div class="questions" v-if="questions.length">
          <div v-for="question in questions" :key="question.id" class="question-card">
            <div class="question-header">
              <span class="question-number">Q{{ question.number }}</span>
              <span class="question-year">{{ question.exam_year }}</span>
              <span v-if="question.subject" class="question-subject">{{ question.subject }}</span>
            </div>
            <div class="question-content">
              <p>{{ question.statement_preview }}</p>
            </div>
            <div v-if="question.correct_answer" class="question-answer">
              <strong>Resposta: {{ question.correct_answer }}</strong>
            </div>
          </div>
        </div>

        <div class="pagination" v-if="pagination.pages > 1">
          <button 
            @click="changePage(pagination.page - 1)" 
            :disabled="!pagination.has_prev"
          >
            Anterior
          </button>
          <span>Página {{ pagination.page }} de {{ pagination.pages }}</span>
          <button 
            @click="changePage(pagination.page + 1)" 
            :disabled="!pagination.has_next"
          >
            Próxima
          </button>
        </div>
      </div>

      <!-- Stats Tab -->
      <div v-if="activeTab === 'stats'" class="tab-content">
        <div class="stats-grid">
          <div class="stat-card">
            <h3>{{ stats.total_questions }}</h3>
            <p>Questões Totais</p>
          </div>
          <div class="stat-card">
            <h3>{{ stats.total_alternatives }}</h3>
            <p>Alternativas</p>
          </div>
          <div class="stat-card">
            <h3>{{ stats.total_answer_keys }}</h3>
            <p>Gabaritos</p>
          </div>
          <div class="stat-card">
            <h3>{{ stats.years_available?.length || 0 }}</h3>
            <p>Anos Disponíveis</p>
          </div>
        </div>

        <div class="details">
          <div class="detail-section">
            <h4>Anos Disponíveis:</h4>
            <div class="tags">
              <span v-for="year in stats.years_available" :key="year" class="tag">
                {{ year }}
              </span>
            </div>
          </div>

          <div class="detail-section">
            <h4>Matérias:</h4>
            <div class="tags">
              <span v-for="subject in stats.subjects" :key="subject" class="tag">
                {{ subject }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import api from './services/api.js'

export default {
  name: 'App',
  setup() {
    const activeTab = ref('search')
    const stats = ref({})
    const questions = ref([])
    const filters = ref({
      year: '',
      subject: '',
      size: 20
    })
    const pagination = ref({})

    const loadStats = async () => {
      try {
        const response = await api.get('/stats')
        stats.value = response.data
      } catch (error) {
        console.error('Error loading stats:', error)
      }
    }

    const loadQuestions = async (page = 1) => {
      try {
        const params = {
          page,
          size: filters.value.size || 20
        }
        
        if (filters.value.year) params.year = filters.value.year
        if (filters.value.subject) params.subject = filters.value.subject

        const response = await api.get('/questions', { params })
        questions.value = response.data.items
        pagination.value = {
          page: response.data.page,
          pages: response.data.pages,
          has_prev: response.data.has_prev,
          has_next: response.data.has_next,
          total: response.data.total
        }
      } catch (error) {
        console.error('Error loading questions:', error)
      }
    }

    const changePage = (newPage) => {
      if (newPage >= 1 && newPage <= pagination.value.pages) {
        loadQuestions(newPage)
      }
    }

    onMounted(() => {
      loadStats()
      loadQuestions()
    })

    return {
      activeTab,
      stats,
      questions,
      filters,
      pagination,
      loadQuestions,
      changePage
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  background: #f5f5f5;
}

#app {
  min-height: 100vh;
}

.header {
  background: white;
  padding: 1rem 2rem;
  border-bottom: 1px solid #eee;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.header h1 {
  color: #333;
  margin-bottom: 1rem;
}

.header nav button {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  padding: 0.5rem 1rem;
  margin-right: 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.header nav button:hover {
  background: #e9ecef;
}

.header nav button.active {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

.main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.filters {
  background: white;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.filters select, .filters input {
  flex: 1;
  min-width: 150px;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.question-card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: transform 0.2s;
}

.question-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.question-header {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  align-items: center;
}

.question-number {
  background: #007bff;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-weight: bold;
}

.question-year {
  background: #28a745;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.question-subject {
  background: #ffc107;
  color: #212529;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.question-content {
  margin-bottom: 1rem;
  line-height: 1.6;
}

.question-answer {
  color: #007bff;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 2rem;
}

.pagination button {
  background: #007bff;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.pagination button:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stat-card h3 {
  font-size: 2rem;
  color: #007bff;
  margin-bottom: 0.5rem;
}

.details {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.detail-section {
  margin-bottom: 2rem;
}

.detail-section h4 {
  margin-bottom: 1rem;
  color: #333;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.tag {
  background: #e9ecef;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.875rem;
}
</style>
