<template>
  <div class="project-edit">
    <page-card title="编辑项目">
      <loading-container :loading="loading">
        <el-form
          ref="form"
          :model="form"
          :rules="rules"
          label-width="120px"
          style="max-width: 800px"
        >
          <el-form-item label="项目名称" prop="name">
            <el-input v-model="form.name" placeholder="请输入项目名称"></el-input>
          </el-form-item>

          <el-form-item label="项目描述" prop="description">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="4"
              placeholder="请输入项目描述"
            ></el-input>
          </el-form-item>

          <el-form-item label="原始文案" prop="original_script">
            <el-input
              v-model="form.original_script"
              type="textarea"
              :rows="8"
              placeholder="请输入原始文案内容"
            ></el-input>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :loading="submitting" @click="handleSubmit">
              保存
            </el-button>
            <el-button @click="handleCancel">取消</el-button>
          </el-form-item>
        </el-form>
      </loading-container>
    </page-card>
  </div>
</template>

<script>
import { mapActions } from 'vuex';
import PageCard from '@/components/common/PageCard.vue';
import LoadingContainer from '@/components/common/LoadingContainer.vue';

export default {
  name: 'ProjectEdit',
  components: {
    PageCard,
    LoadingContainer,
  },
  data() {
    return {
      loading: false,
      submitting: false,
      form: {
        name: '',
        description: '',
        original_script: '',
      },
      rules: {
        name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
        original_script: [{ required: true, message: '请输入原始文案', trigger: 'blur' }],
      },
    };
  },
  created() {
    this.fetchData();
  },
  methods: {
    ...mapActions('projects', ['fetchProject', 'updateProject']),

    async fetchData() {
      this.loading = true;
      try {
        const project = await this.fetchProject(this.$route.params.id);
        this.form = {
          name: project.name,
          description: project.description,
          original_script: project.original_script,
        };
      } catch (error) {
        console.error('Failed to fetch project:', error);
        this.$message.error('加载项目失败');
      } finally {
        this.loading = false;
      }
    },

    async handleSubmit() {
      try {
        await this.$refs.form.validate();
        this.submitting = true;

        await this.updateProject({
          id: this.$route.params.id,
          data: this.form,
        });
        this.$message.success('保存成功');
        this.$router.push(`/projects/${this.$route.params.id}`);
      } catch (error) {
        if (error !== false) {
          console.error('Failed to update project:', error);
        }
      } finally {
        this.submitting = false;
      }
    },

    handleCancel() {
      this.$router.back();
    },
  },
};
</script>
