"""Smoke tests for page rendering — verify all pages load and contain expected elements."""

import pytest
from httpx import ASGITransport, AsyncClient

from release_manager.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestPageLoads:
    @pytest.mark.asyncio
    async def test_release_scope_page(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "Release Scope" in resp.text

    @pytest.mark.asyncio
    async def test_draft_page(self, client):
        resp = await client.get("/draft")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_releases_page(self, client):
        resp = await client.get("/releases")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_deploy_page(self, client):
        resp = await client.get("/deploy")
        assert resp.status_code == 200
        assert "Deploy Tracker" in resp.text


class TestReleaseScopeElements:
    @pytest.mark.asyncio
    async def test_has_nav_tooltips(self, client):
        resp = await client.get("/")
        html = resp.text
        # Nav tooltips contain new names
        assert "Release Scope" in html
        assert "Release Task Scope" in html

    @pytest.mark.asyncio
    async def test_has_credentials_fields(self, client):
        resp = await client.get("/")
        assert "git_username" in resp.text
        assert "git_token" in resp.text
        assert "linear_api_key" in resp.text

    @pytest.mark.asyncio
    async def test_description_text(self, client):
        resp = await client.get("/")
        assert "Collect tasks between two versions" in resp.text

    @pytest.mark.asyncio
    async def test_no_old_names(self, client):
        resp = await client.get("/")
        # Old names should not appear
        assert ">Repositories<" not in resp.text
        assert "Scan & Import" not in resp.text


class TestDeployElements:
    @pytest.mark.asyncio
    async def test_has_save_release_button(self, client):
        resp = await client.get("/deploy")
        assert "Save Release" in resp.text

    @pytest.mark.asyncio
    async def test_has_copy_md_button(self, client):
        resp = await client.get("/deploy")
        assert "Copy MD" in resp.text

    @pytest.mark.asyncio
    async def test_has_release_number_field(self, client):
        resp = await client.get("/deploy")
        assert "Release" in resp.text
        assert 'id="snapshot-name"' in resp.text

    @pytest.mark.asyncio
    async def test_has_cluster_selector(self, client):
        resp = await client.get("/deploy")
        assert "aiphoria-qa" in resp.text

    @pytest.mark.asyncio
    async def test_description_no_testing(self, client):
        resp = await client.get("/deploy")
        # Should not mention testing
        assert "after testing" not in resp.text

    @pytest.mark.asyncio
    async def test_has_author_updated_columns(self, client):
        resp = await client.get("/deploy")
        assert "Author" in resp.text
        assert "Updated" in resp.text

    @pytest.mark.asyncio
    async def test_no_compare_with_release(self, client):
        resp = await client.get("/deploy")
        assert "Compare with release" not in resp.text

    @pytest.mark.asyncio
    async def test_no_snapshot_button(self, client):
        resp = await client.get("/deploy")
        # Old "Snapshot" button should be gone
        assert ">Snapshot<" not in resp.text

    @pytest.mark.asyncio
    async def test_triton_models_section(self, client):
        resp = await client.get("/deploy")
        assert "Triton Models" in resp.text
        assert "hlir/v2/20250429-1" in resp.text

    @pytest.mark.asyncio
    async def test_infra_sections(self, client):
        resp = await client.get("/deploy")
        assert "Platform-deploy commit" in resp.text
        assert "Ansible (sip-deploy)" in resp.text


class TestRemoteRepoListPartial:
    @pytest.mark.asyncio
    async def test_loads_repo_list(self, client):
        resp = await client.post("/partials/remote-repo-list")
        assert resp.status_code == 200
        html = resp.text
        assert "From Tag" in html
        assert "To Tag" in html

    @pytest.mark.asyncio
    async def test_has_rasa_separator(self, client):
        resp = await client.post("/partials/remote-repo-list")
        assert "RASA" in resp.text

    @pytest.mark.asyncio
    async def test_repos_sorted_alphabetically(self, client):
        resp = await client.post("/partials/remote-repo-list")
        html = resp.text
        # agent-bridge should appear before studio
        pos_agent = html.find("agent-bridge")
        pos_studio = html.find("studio")
        if pos_agent >= 0 and pos_studio >= 0:
            assert pos_agent < pos_studio