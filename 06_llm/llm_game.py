import streamlit as st
from openai import OpenAI 
import openai
from dotenv import load_dotenv
import json 

load_dotenv()
client = OpenAI()

prompt = """ 
너는 '누가 거짓말을 하고 있을까?'의 게임 마스터야.
모든 응답은 반드신 유효한 JSON 형식으로, 자연스러운 한국어로 해. 
JSON 구조는 항상 {'message': '사용자에게 보여줄 메시지', 'master': {'내부 데이터'}} 형식으로 유지해.
게임은 아래 규칙을 철저히 따라 진행해.

### 게임 규칙 ###
1. 시나리오 생성:
    - 3명의 용의자 중 누가 거짓말을 하는지 찾아내는 미스터리 게임으로, 매 게임마다 새로운 시나리오를 만들어.
    - 용의자: 총 3명으로, 각 용의자는 이름, 직업, 성별, 배경(피해자와의 관계나 특성)을 생성해.
    - 피해자: 간단한 이름이나 역할로 생성 (예시: 집주인, 손님)
    - 범인: 용의자 3명 중 랜덤으로 1명 선택 (거짓말하는 사람)
    - 장소: 사건이 일어날만한 장소를 생성해. (예시: 서재, 테라스, 유람선)
    - 무기: 범죄에 사용될 수 있는 도구를 생성해. (예시: 망치, 밧줄, 주사기)
    - 사건 유형 랜덤: 살해당했다, 독살당했다, 도난당했다 중 하나.
    - 시나리오 출력 형식: message에 "[장소]에서 [피해자]가 [사건 유형]. 용의자는 총 3명. 누가 거짓말을 진술하고 있을까?"와 용의자 목록.
    - master에 {"suspects": [{"name": "...", "job": "...", "gender": "...", "background": "..."}], "location": "...", "weapon": "...", "victim": "...", "event_type": "...", "liar": "범인 이름"} 저장.

2. 사건 카드:
    -'시작' 입력 시, 5개의 고유한 사건 카드를 미리 생성해 master['all_cards']에 저장. 각 카드는 인물/장소/무기 관련 힌트로, 사건과 연결되고 범인을 암시해야 해.
    - '사건 카드 보기' 입력 시,  master['all_cards']에서 아직 공개되지 않은 카드를 하나 선택해 master['revealed_cards']에 추가하고, message에 '사건 카드: [카드 내용] 출력.
    - master['revealed_cards']가 5개가 되면, '사건 카드 보기' 입력 시 message에 '"모든 사건 카드를 열람하였습니다.' 출력.
    - 예시 카드: '[피해자]가 [사건 유형]되기 전 금전문제로 큰 소리로 다퉜음.' 또는 '출입은 총 2명이였고, 그 중 1명은 [무기 관련] 흔적이 있음.'
    - 응답 예시: {'message': '사건 카드: [카드 내용]', 'master': {'suspects': [...], 'all_cards': ['카드1', '카드2', ...], 'revealed_cards': ['카드1'], ...}}
    
3. 질문하기:
    - 질문 입력 시, 모든 용의자의 응답을 생성해 message에 채팅 형식으로 "- [이름]: [응답]" 출력. 시나리오를 반복하지 말고, 질문에 대한 응답만 제공.
    - 최대 2번 질문 허용. master["question_count"]를 증가시키고, 초과 시 message에 '더 이상 질문할 수 없음' 출력.
    - 진실 말하는 사람: 시나리오와 일관된 진실. 배경 반영해 자연스럽게.
    - 거짓말하는 사람 (범인): 모순되는 거짓말. 하지만 미묘하게 혼란스럽게.
    - master["question_count"] 업데이트.
    - 응답 예시: {"message": "- [이름1]: [응답1]\n- [이름2]: [응답2]\n- [이름3]: [응답3]", "master": {"suspects": [...], "question_count": 1, ...}}

4. 게임 진행:
   - '시작'으로 게임 시작. 시나리오 출력.
   - '사건 카드 보기': 카드 하나 공개 (최대 5개).
   - '질문': 질문 처리 (최대 2번).
   - '지목: [용의자 이름]': 정답 확인. 맞으면 '정답입니다! 이유: [모순 설명]'. 틀리면 '땡! 이유: [모순 설명]'.
   - '종료': 게임 종료, master 초기화.
   - master로 내부 상태 유지 (all_cards, revealed_cards, question_count 등).

항상 JSON만 출력. 오류 시 {"error": "오류 메시지"}.

"""

if 'game_state' not in st.session_state:
    st.session_state.game_state = {
        'history': [],         
        'game_started': False, 
        'scenario': {}, 
        'current_response': {}, 
        'revealed_cards': [],
        'question_responses': [],
        'check_result': None
    }

# LLM 
def llm(user_input):
    messages = [
        {
            'role': 'system',
            'content': prompt
        }
    ] + st.session_state.game_state['history'] + [
        {
            'role': 'user',
            'content': user_input
        }
    ]
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=messages,
        temperature=1
    )

    llm_response = response.choices[0].message.content

    json_response = json.loads(llm_response)
    st.session_state.game_state['history'].append({
        'role': 'user',
        'content': user_input
    })
    st.session_state.game_state['history'].append({
        'role': 'assistant',
        'content': llm_response
    })

    # 사건 카드 업데이트
    if user_input == '사건 카드 보기' and 'error' not in json_response:
        if json_response['message'] != '모든 사건 카드를 열람하였습니다.':
            st.session_state.game_state['revealed_cards'].append(json_response['message'])

    # 질문 업데이트
    if 'error' not in json_response:
        if not user_input.startswith('지목:'):
            if user_input != '시작' and user_input != '사건 카드 보기' and not user_input.startswith('지목:'):
                if json_response['message'] != '더 이상 질문할 수 없습니다.':
                    st.session_state.game_state['question_responses'].append({
                        'question': user_input,
                        'response': json_response['message']
                    })
        
        else:
            st.session_state.game_state['check_result'] = json_response['message']

    return json_response


st.title('누가 거짓말을 하고 있을까?🕵️')

# 초기 화면
if not st.session_state.game_state['game_started']:
    if st.button('게임 시작하기', key='start_button'):
        st.session_state.game_state['game_started'] = True 
        st.session_state.game_state['revealed_cards'] = []
        st.session_state.game_state['question_responses'] = []
        response = llm('시작')
        if 'error' not in response:
            st.session_state.game_state['current_response'] = response
            st.session_state.game_state['scenario'] = response
        st.rerun()

else:
    with st.container():
        scenario = st.session_state.game_state.get('scenario', {})
        if 'message' in scenario:
            # 시나리오
            st.subheader('사건 개요')
            st.write(scenario['message'])

            # 용의자
            suspects = scenario.get('master', {}).get('suspects', [])
            if suspects:
                cols = st.columns(3)
                for i, suspect in enumerate(suspects):
                    with cols[i]:
                        st.subheader(f'용의자 {i+1}')
                        st.write(f'이름: {suspect['name']}')
                        st.write(f'성별: {suspect['gender']}')
                        st.write(f'직업: {suspect['job']}')
                        st.write(f'배경: {suspect['background']}')

    # 사건카드
    with st.expander('사건 카드 보기', expanded=True):
        if st.session_state.game_state['revealed_cards']:
            for card in st.session_state.game_state['revealed_cards']:
                st.write(card)

        reamain_cards = 5 - len(st.session_state.game_state['revealed_cards'])
        st.write(f'남은 사건 카드: {reamain_cards}')

        if reamain_cards > 0:
            if st.button('사건 카드 보기', key='card_button'):
                card_response = llm('사건 카드 보기')
                if 'error' not in card_response:
                    st.session_state.game_state['current_response'] = card_response
                    st.rerun()


    # 질문하기
    with st.expander('질문하기', expanded=True):
        question = st.text_input('질문을 입력하세요.', key = 'question_input')
        if st.button('전송', key='question_submit'):
            if question:
                q_response = llm(question)
                if 'error' not in q_response:
                    st.session_state.game_state['current_response'] = q_response
                    st.rerun()
                else:
                    st.error(q_response['error'])

        st.subheader('답변')
        if st.session_state.game_state['question_responses']:
            for q_response in st.session_state.game_state['question_responses']:
                st.write(f'질문: {q_response['question']}')
                st.write(q_response['response'])
            
            reamain_q = 2 - len(st.session_state.game_state['question_responses'])
            st.write(f'가능한 질문 수: {reamain_q}')

    with st.container():
        # 범인 지목
        st.subheader('범인 맞추기')
        check = st.text_input('지목할 용의자의 이름을 입력하세요', key='check_input')
        if st.button('전송', 'check_submit'):
            if check:
                response = llm(f'지목: {check}')
                if 'error' not in response:
                    st.rerun()
        
        if st.session_state.game_state['check_result']:
            st.write(st.session_state.game_state['check_result'])

    with st.container():
        # 게임 종료
        col1, col2 = st.columns(2)
        with col1:
            if st.button('게임 종료', key='end_button'):
                response = llm('종료')
                st.session_state.game_state = {
                    'history': [], 
                    'game_started': False,
                    'scenario': {},
                    'revealed_cards': [],
                    'question_responses': []
                    }
                st.rerun()
        with col2:
            if st.button('게임 재시작', key='restart_button'):
                st.session_state.game_state = {
                    'history': [], 
                    'game_started': True,
                    'scenario': {},
                    'revealed_cards': [],
                    'question_responses': []
                    }
                response = llm('시작')
                if 'error' not in response:
                    st.session_state.game_state['current_response'] = response
                st.rerun()